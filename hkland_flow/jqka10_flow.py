import datetime
import logging
import re
import traceback

import execjs
import requests

from hkland_flow.configs import DC_HOST, DC_PORT, DC_USER, DC_DB, DC_PASSWD, SPIDER_MYSQL_HOST, SPIDER_MYSQL_PORT, \
    SPIDER_MYSQL_USER, SPIDER_MYSQL_PASSWORD, SPIDER_MYSQL_DB
from hkland_flow.sql_pool import PyMysqlPoolBase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SFLgthisdataspiderSpider(object):
    dc_cfg = {
        "host": DC_HOST,
        "port": DC_PORT,
        "user": DC_USER,
        "password": DC_PASSWD,
        "db": DC_DB,
    }

    spider_cfg = {
        "host": SPIDER_MYSQL_HOST,
        "port": SPIDER_MYSQL_PORT,
        "user": SPIDER_MYSQL_USER,
        "password": SPIDER_MYSQL_PASSWORD,
        "db": SPIDER_MYSQL_DB,
    }

    def __init__(self):
        self.headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            # 'hexin-v': '',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
            'Accept': 'text/html, */*; q=0.01',
            'Referer': 'http://data.10jqka.com.cn/hgt/ggtb/',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
        }
        self.base_url = 'http://data.10jqka.com.cn/hgt/{}/'
        # 1-沪股通 2-港股通（沪）3-深股通，4-港股通（深）5-港股通（沪深）
        self.category_map = {
            'hgtb': ('沪股通', 1),
            'ggtb': ('港股通(沪)', 2),
            'sgtb': ('深股通', 3),
            'ggtbs': ('港股通(深)', 4),
        }
        self.today = datetime.datetime.today().strftime("%Y-%m-%d")
        self.table_name = 'hkland_flow_jqka10'

    def _init_pool(self, cfg: dict):
        """
        eg.
        conf = {
                "host": LOCAL_MYSQL_HOST,
                "port": LOCAL_MYSQL_PORT,
                "user": LOCAL_MYSQL_USER,
                "password": LOCAL_MYSQL_PASSWORD,
                "db": LOCAL_MYSQL_DB,
        }
        :param cfg:
        :return:
        """
        pool = PyMysqlPoolBase(**cfg)
        return pool

    @property
    def cookies(self):
        with open('jqka.js', 'r') as f:
            jscont = f.read()
        cont = execjs.compile(jscont)
        cookie_v = cont.call('v')
        cookies = {
            'v': cookie_v,
        }
        return cookies

    def get(self, url):
        resp = requests.get(url, headers=self.headers, cookies=self.cookies)
        if resp.status_code == 200:
            return resp.text

    def _create_table(self):
        spider = self._init_pool(self.spider_cfg)
        sql = '''
        CREATE TABLE IF NOT EXISTS `{}` (
          `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
          `DateTime` datetime NOT NULL COMMENT '交易时间',
          `ShHkFlow` decimal(19,4) NOT NULL COMMENT '沪股通/港股通(沪)当日资金流向(万）',
          `ShHkBalance` decimal(19,4) NOT NULL COMMENT '沪股通/港股通(沪)当日资金余额（万）',
          `SzHkFlow` decimal(19,4) NOT NULL COMMENT '深股通/港股通(深)当日资金流向(万）',
          `SzHkBalance` decimal(19,4) NOT NULL COMMENT '深股通/港股通(深)当日资金余额（万）',
          `Netinflow` decimal(19,4) NOT NULL COMMENT '南北向资金,当日净流入',
          `Category` tinyint(4) NOT NULL COMMENT '类别:1 南向, 2 北向',
          `CREATETIMEJZ` datetime DEFAULT CURRENT_TIMESTAMP,
          `UPDATETIMEJZ` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          UNIQUE KEY `unique_key2` (`DateTime`,`Category`),
          KEY `DateTime` (`DateTime`) USING BTREE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='陆港通-实时资金流向-同花顺数据源';
        '''.format(self.table_name)
        spider.insert(sql)
        spider.dispose()

    def _check_if_trading_today(self, category):
        """检查下当前方向是否交易"""
        dc = self._init_pool(self.dc_cfg)
        tradingtype = self.category_map.get(category)[1]
        sql = 'select IfTradingDay from hkland_shszhktradingday where TradingType={} and EndDate = "{}";'.format(
            tradingtype, self.today)
        ret = True if dc.select_one(sql).get('IfTradingDay') == 1 else False
        return ret

    def contract_sql(self, to_insert: dict, table: str, update_fields: list):
        ks = []
        vs = []
        for k in to_insert:
            ks.append(k)
            vs.append(to_insert.get(k))
        fields_str = "(" + ",".join(ks) + ")"
        values_str = "(" + "%s," * (len(vs) - 1) + "%s" + ")"
        base_sql = '''INSERT INTO `{}` '''.format(table) + fields_str + ''' values ''' + values_str
        on_update_sql = ''' ON DUPLICATE KEY UPDATE '''
        update_vs = []
        for update_field in update_fields:
            on_update_sql += '{}=%s,'.format(update_field)
            update_vs.append(to_insert.get(update_field))
        on_update_sql = on_update_sql.rstrip(",")
        sql = base_sql + on_update_sql + """;"""
        vs.extend(update_vs)
        return sql, tuple(vs)

    def _save(self, to_insert, table, update_fields: list):
        spider = self._init_pool(self.spider_cfg)
        try:
            insert_sql, values = self.contract_sql(to_insert, table, update_fields)
            count = spider.insert(insert_sql, values)
        except:
            traceback.print_exc()
            logger.warning("失败")
            count = None
        else:
            if count:
                logger.info("更入新数据 {}".format(to_insert))
        finally:
            spider.dispose()
        return count

    def _start(self):
        self._create_table()
        for category in self.category_map:
            is_trading = self._check_if_trading_today(category)
            if not is_trading:
                logger.info("{} 该方向数据今日关闭".format(self.category_map.get(category)[0]))
                continue
            else:
                url = self.base_url.format(category)
                page = self.get(url)
                ret = re.findall(r"var dataDay = (.*);", page)
                if ret:
                    datas = eval(ret[0])[0]
                    for data in datas:
                        item = dict()
                        item['Date'] = self.today + " " + data[0]
                        item['Flow'] = float(data[1])
                        item['Balance'] = float(data[2])
                        item['Category'] = self.category_map.get(category)[0]
                        item['CategoryCode'] = category
                        print(item)   # {'Date': '2020-04-07 09:44', 'Flow': -0.86, 'Balance': 420.86, 'Category': '港股通(沪)', 'CategoryCode': 'ggtb'}
                        # table = "lgt_north_money_data_10jqka" if self.category_map.get(category)[1] in (1, 3) else "lgt_south_money_data_10jqka"
                        # self._save(item, table, update_fields=['Date', 'Flow', 'Balance', 'Category', 'CategoryCode'])


if __name__ == "__main__":
    sf = SFLgthisdataspiderSpider()
    # print(sf.cookies)
    sf._start()
