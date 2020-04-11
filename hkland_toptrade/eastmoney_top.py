# -*- coding: utf-8 -*-

import datetime
import json
import re

import requests

from hkland_toptrade.base_spider import BaseSpider


class EMLgttop10tradedsharesspiderSpider(BaseSpider):
    """十大成交股 东财数据源 """
    def __init__(self, day: str):
        self.headers = {
            'Referer': 'http://data.eastmoney.com/hsgt/top10.html',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        }
        self.day = day    # datetime.datetime.strftime("%Y-%m-%d")
        self.url = 'http://data.eastmoney.com/hsgt/top10/{}.html'.format(day)

    def _get_inner_code_map(self, market_type):
        """https://dd.gildata.com/#/tableShow/27/column///
           https://dd.gildata.com/#/tableShow/718/column///
        """
        juyuan = self._init_pool(self.juyuan_cfg)
        if market_type in ("sh", "sz"):
            sql = 'SELECT SecuCode,InnerCode from SecuMain WHERE SecuCategory in (1, 2) and SecuMarket in (83, 90) and ListedSector in (1, 2, 6, 7);'
        else:
            sql = '''SELECT SecuCode,InnerCode from hk_secumain WHERE SecuCategory in (51, 3, 53, 78) and SecuMarket in (72) and ListedSector in (1, 2, 6, 7);'''
        ret = juyuan.select_all(sql)
        juyuan.dispose()
        info = {}
        for r in ret:
            key = r.get("SecuCode")
            value = r.get('InnerCode')
            info[key] = value
        return info

    def _start(self):
        resp = requests.get(self.url, headers=self.headers)
        if resp.status_code == 200:
            body = resp.text
            # 沪股通十大成交股
            data1 = re.findall('var DATA1 = (.*);', body)[0]
            # 深股通十大成交股
            data2 = re.findall('var DATA2 = (.*);', body)[0]
            # 港股通(沪)十大成交股
            data3 = re.findall('var DATA3 = (.*);', body)[0]
            # 港股通(深)十大成交股
            data4 = re.findall('var DATA4 = (.*);', body)[0]

            sh_innercode_map = self._get_inner_code_map("sh")
            sz_innercode_map = self._get_inner_code_map("sz")
            hk_innercode_map = self._get_inner_code_map("hk")

            for data in [data1, data2, data3, data4]:
                data = json.loads(data)
                top_datas = data.get("data")
                # fields = ['Date', 'SecuCode', 'InnerCode', 'SecuAbbr', 'Close', 'ChangePercent', 'TJME', 'TMRJE',
                #           'TCJJE', 'CategoryCode']
                for top_data in top_datas:
                    item = dict()
                    item['Date'] = self.day   # 时间
                    secu_code = top_data.get("Code")
                    item['SecuCode'] = secu_code  # 证券代码
                    item['SecuAbbr'] = top_data.get("Name")   # 证券简称
                    item['Close'] = top_data.get('Close')  # 收盘价
                    item['ChangePercent'] = top_data.get('ChangePercent')  # 涨跌幅
                    if top_data['MarketType'] == 1.0:
                        item['CategoryCode'] = 'HG'
                        item['Category'] = '沪股通'
                        # 净买额
                        item['TJME'] = top_data['HGTJME']
                        # 买入金额
                        item['TMRJE'] = top_data['HGTMRJE']
                        # # 卖出金额
                        # item['TMCJE'] = top_data['HGTMCJE']
                        # 成交金额
                        item['TCJJE'] = top_data['HGTCJJE']
                        item['InnerCode'] = sh_innercode_map.get(secu_code)

                    elif top_data['MarketType'] == 2.0:
                        item['CategoryCode'] = 'GGh'
                        item['Category'] = '港股通(沪)'
                        # 港股通(沪)净买额(港元）
                        item['TJME'] = top_data['GGTHJME']
                        # 港股通(沪)买入金额(港元）
                        item['TMRJE'] = top_data['GGTHMRJE']
                        # # 港股通(沪)卖出金额(港元）
                        # item['TMCJE'] = top_data['GGTHMCJE']
                        # 港股通(沪)成交金额(港元）
                        item['TCJJE'] = top_data['GGTHCJJE']
                        item['InnerCode'] = hk_innercode_map.get(secu_code)

                    elif top_data['MarketType'] == 3.0:
                        item['CategoryCode'] = 'SG'
                        item['Category'] = '深股通'
                        # 净买额
                        item['TJME'] = top_data['SGTJME']
                        # 买入金额
                        item['TMRJE'] = top_data['SGTMRJE']
                        # # 卖出金额
                        # item['TMCJE'] = top_data['SGTMCJE']
                        # 成交金额
                        item['TCJJE'] = top_data['SGTCJJE']
                        item['InnerCode'] = sz_innercode_map.get(secu_code)

                    elif top_data['MarketType'] == 4.0:
                        item['CategoryCode'] = 'GGs'
                        item['Category'] = '港股通(深)'
                        # 港股通(沪)净买额(港元）
                        item['TJME'] = top_data['GGTSJME']
                        # 港股通(沪)买入金额(港元）
                        item['TMRJE'] = top_data['GGTSMRJE']
                        # # 港股通(沪)卖出金额(港元）
                        # item['TMCJE'] = top_data['GGTSMCJE']
                        # 港股通(沪)成交金额(港元）
                        item['TCJJE'] = top_data['GGTSCJJE']
                        item['InnerCode'] = hk_innercode_map.get(secu_code)

                    else:
                        raise
                    print(item)

    def _create_table(self):
        # fields = ['Date', 'SecuCode', 'InnerCode', 'SecuAbbr', 'Close', 'ChangePercent', 'TJME', 'TMRJE', 'TCJJE', 'CategoryCode',]
        sql = '''
        CREATE TABLE IF NOT EXISTS `hkland_toptrade` (
          `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
          `Date` date NOT NULL COMMENT '时间',
          `SecuCode` varchar(10) COLLATE utf8_bin NOT NULL COMMENT '证券代码',
          `InnerCode` int(11) NOT NULL COMMENT '内部编码',
          `SecuAbbr` varchar(20) COLLATE utf8_bin NOT NULL COMMENT '股票简称',
          `Close` decimal(19,3) NOT NULL COMMENT '收盘价',
          `ChangePercent` decimal(19,5) NOT NULL COMMENT '涨跌幅',
          `TJME` decimal(19,3) NOT NULL COMMENT '净买额（元/港元）',
          `TMRJE` decimal(19,3) NOT NULL COMMENT '买入金额（元/港元）',
          `TCJJE` decimal(19,3) NOT NULL COMMENT '成交金额（元/港元）',
          `CategoryCode` varchar(10) COLLATE utf8_bin DEFAULT NULL COMMENT '类别代码:GGh: 港股通(沪), GGs: 港股通(深), HG: 沪股通, SG: 深股通',
          `CMFID` bigint(20) NOT NULL COMMENT '来源ID',
          `CMFTime` datetime NOT NULL COMMENT '来源日期',
          `CREATETIMEJZ` datetime DEFAULT CURRENT_TIMESTAMP,
          `UPDATETIMEJZ` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          UNIQUE KEY `un` (`SecuCode`,`Date`,`CategoryCode`) USING BTREE,
          UNIQUE KEY `un2` (`InnerCode`,`Date`,`CategoryCode`) USING BTREE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='陆港通十大成交股';
        '''
        product = self._init_pool(self.product_cfg)
        product.insert(sql)
        product.dispose()


if __name__ == "__main__":
    t_day = datetime.datetime.today()
    day = t_day - datetime.timedelta(days=4)
    day_str = day.strftime("%Y-%m-%d")
    top10 = EMLgttop10tradedsharesspiderSpider(day_str)
    top10._create_table()
    top10._start()
