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
            for data in [data1, data2, data3, data4]:
                data = json.loads(data)
                top_datas = data.get("data")
                # print(top_datas)
                # print()
                for top_data in top_datas:
                    item = dict()
                    item['Date'] = self.day   # 时间
                    item['SecuCode'] = top_data.get("Code")  # 证券代码
                    item['SecuName'] = top_data.get("Name")   # 证券简称
                    item['Close'] = top_data.get('Close')  # 收盘价
                    item['ChangePercent'] = top_data.get('ChangePercent')  # 涨跌幅
                    if top_data['MarketType'] == 1.0:
                        item['CategoryCode'] = 'HG'
                        item['Category'] = '沪股通'
                        # 净买额
                        item['TJME'] = top_data['HGTJME']
                        # 买入金额
                        item['TMRJE'] = top_data['HGTMRJE']
                        # 卖出金额
                        item['TMCJE'] = top_data['HGTMCJE']
                        # 成交金额
                        item['TCJJE'] = top_data['HGTCJJE']

                    elif top_data['MarketType'] == 2.0:
                        item['CategoryCode'] = 'GGh'
                        item['Category'] = '港股通(沪)'
                        # 港股通(沪)净买额(港元）
                        item['TJME'] = top_data['GGTHJME']
                        # 港股通(沪)买入金额(港元）
                        item['TMRJE'] = top_data['GGTHMRJE']
                        # 港股通(沪)卖出金额(港元）
                        item['TMCJE'] = top_data['GGTHMCJE']
                        # 港股通(沪)成交金额(港元）
                        item['TCJJE'] = top_data['GGTHCJJE']
                    elif top_data['MarketType'] == 3.0:
                        item['CategoryCode'] = 'SG'
                        item['Category'] = '深股通'
                        # 净买额
                        item['TJME'] = top_data['SGTJME']
                        # 买入金额
                        item['TMRJE'] = top_data['SGTMRJE']
                        # 卖出金额
                        item['TMCJE'] = top_data['SGTMCJE']
                        # 成交金额
                        item['TCJJE'] = top_data['SGTCJJE']
                    elif top_data['MarketType'] == 4.0:
                        item['CategoryCode'] = 'GGs'
                        item['Category'] = '港股通(深)'
                        # 港股通(沪)净买额(港元）
                        item['TJME'] = top_data['GGTSJME']
                        # 港股通(沪)买入金额(港元）
                        item['TMRJE'] = top_data['GGTSMRJE']
                        # 港股通(沪)卖出金额(港元）
                        item['TMCJE'] = top_data['GGTSMCJE']
                        # 港股通(沪)成交金额(港元）
                        item['TCJJE'] = top_data['GGTSCJJE']
                    else:
                        raise
                    print(item)


if __name__ == "__main__":
    t_day = datetime.datetime.today()
    day = t_day - datetime.timedelta(days=4)
    day_str = day.strftime("%Y-%m-%d")
    top10 = EMLgttop10tradedsharesspiderSpider(day_str)
    top10._start()