"""
2023 TTG
"""
import ccxt
from tabulate import tabulate
import pandas as pd
from config import api_config
import os
import dataframe_image as dfi
from PIL import Image
import numpy as np
import json
import base64
import hashlib
import traceback
from datetime import datetime
import requests

proxy = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
wechat_webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=461a8d04-fea5-4a85-bede-f88dbc781c02"
root_path = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径


# 企业微信通知
def send_wechat_work_msg(content):
    """
    企业微信发送通知给机器人

    :param content:    发送的消息内容
    """
    try:
        # 构建企业微信机器人的消息体。参考文档：https://developer.work.weixin.qq.com/document/path/91770
        data = {
            "msgtype": "text",
            "text": {
                "content": content + '\n' + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        # 使用requests发送通知
        r = requests.post(wechat_webhook_url, data=json.dumps(data), timeout=10, proxies=proxy)
        print(f'调用企业微信接口返回： {r.text}')
        print('成功发送企业微信')
    except Exception as e:
        print(f"发送企业微信失败:{e}")
        print(traceback.format_exc())


# 上传图片，解析bytes
class MyEncoder(json.JSONEncoder):
    """
    定义一个JSON编码器，用来处理默认json无法转换的数据类型，例如：图片
    """

    def default(self, obj):
        """
        只要检查到了是bytes类型的数据就把它转为str类型
        :param obj:
        :return:
        """
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


# 企业微信发送图片
def send_wechat_work_img(file_path):
    """
    企业微信发送图片
    :param file_path:       本地图片的位置
    :return:
    """
    try:
        # 判断图片是否存在
        if not os.path.exists(file_path):  # 图片不存在，跳过该程序
            print('找不到图片')
            return
        # 读取图片文件
        with open(file_path, 'rb') as f:
            image_content = f.read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')  # 将图片进行编码，转成base64格式
        md5 = hashlib.md5()  # 构建md5
        md5.update(image_content)  # 对于base64格式的图片进行md5加密
        image_md5 = md5.hexdigest()  # 获取图片加密后的hex码，这就是常见的md5码
        data = {
            'msgtype': 'image',
            'image': {
                'base64': image_base64,
                'md5': image_md5
            }
        }
        # 服务器上传bytes图片的时候，json.dumps解析会出错，需要自己手动去转一下
        r = requests.post(wechat_webhook_url, data=json.dumps(data, cls=MyEncoder, indent=4), timeout=10, proxies=proxy)
        print(f'调用企业微信接口返回： {r.text}')
        print('成功发送企业微信')
    except Exception as e:
        print(f"发送企业微信失败:{e}")
        print(traceback.format_exc())
    finally:
        # 判断图片是否存在
        if os.path.exists(file_path):  # 不管有没有发送成功，最后都去删除图片
            os.remove(file_path)


def make_image(long_df, short_df):
    lsll = os.path.join(root_path, 'long_df.png')
    ssll = os.path.join(root_path, 'short_df.png')
    dfi.export(long_df, lsll, table_conversion='matplotlib')
    dfi.export(short_df, ssll, table_conversion='matplotlib')

    long_img = Image.open(lsll)
    short_img = Image.open(ssll)

    total_width = long_img.width + short_img.width
    max_height = max(long_img.height, short_img.height)

    new_img = Image.new('RGB', (total_width, max_height), (255, 255, 255))

    new_img.paste(long_img, (0, 0))
    new_img.paste(short_img, (long_img.width, 0))

    pos_pic_path = os.path.join(root_path, 'combined.png')
    new_img.save(pos_pic_path)
    send_wechat_work_img(pos_pic_path)


def run_check():
    exchange = ccxt.binance(api_config)  # 交易所api
    account_info = exchange.fapiPrivateV2_get_account()['positions']

    balances = exchange.fetch_balance({'type': 'future'})
    for coin, balance in balances['total'].items():
        if balance != 0:
            print(f"合约保证金 {coin}: {balance}")

    print("*" * 50)
    # 获取所有的合约持仓信息
    positions = exchange.fapiPrivateV2_get_positionrisk()

    long = 0
    short = 0
    long_l = []
    short_l = []
    # 循环遍历所有持仓信息
    for position in positions:
        # 如果持仓数量不为0，则输出
        als = position['positionAmt']
        als = float(als)
        if float(als) != 0:
            entryPrice = position['entryPrice']  # 开仓时的成交价格，
            markPrice = position['markPrice']  # 当前合约的标记价格
            value = als * float(markPrice)
            if als > 0:
                long += value
                long_l.append((position['symbol'], "long", als, value))
            else:
                short += value
                short_l.append((position['symbol'], "short", als, value))

    headers = ["Symbol", "Pos", "Amount", "Value (U)"]

    long_df = pd.DataFrame(long_l, columns=headers)
    short_df = pd.DataFrame(short_l, columns=headers)

    long_df = long_df.reindex(np.abs(long_df[headers[-1]]).sort_values(ascending=False).index).reset_index(drop=True)
    short_df = short_df.reindex(np.abs(short_df[headers[-1]]).sort_values(ascending=False).index).reset_index(drop=True)

    long_df["Asset ratio"] = (long_df["Value (U)"] / long_df["Value (U)"].sum() * 100).apply(
        lambda x: '{:.1f}%'.format(x))
    short_df["Asset ratio"] = (short_df["Value (U)"] / short_df["Value (U)"].sum() * 100).apply(
        lambda x: '{:.1f}%'.format(x))

    headers += ["Asset ratio"]
    long_table = tabulate(long_df, headers=headers, tablefmt="grid")
    short_table = tabulate(short_df, headers=headers, tablefmt="grid")

    print("多头仓位：")
    print(long_table)
    print("\n空头仓位：")
    print(short_table)

    rattt = abs(long) / abs(short)

    msg = "多头: %.2f U 空头: %.2f U \n" % (long, short)
    msg += "多空比: %.2f " % (rattt)

    print(msg)
    print("*" * 50)

    # # 获取所有币种的余额信息
    # balances = exchange.fetch_balance()

    # # 循环遍历所有余额信息
    # for coin, balance in balances['total'].items():
    #     # 如果余额不为0且币种名称不是USDT，则输出
    #     if balance != 0:
    #         print(f"现货 {coin}: {balance}") 

    make_image(long_df, short_df)
    send_wechat_work_msg(msg)

    return long_df, short_df, long, short, rattt


if __name__ == "__main__":
    run_check()
