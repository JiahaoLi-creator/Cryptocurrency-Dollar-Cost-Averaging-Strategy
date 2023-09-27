import time
import pandas as pd
from BL转仓代码.BL合约转仓现货.program.function import *
import ccxt
import datetime

# 创建交易所对象
exchange = ccxt.binance(api_config)
count = 0  # 下单次数
# ===计算转仓币种最小下单量等信息
# 获取合约的精度信息
exg_info_swap = get_exchange_info(exchange)
exg_info_swap = exg_info_swap[exg_info_swap['symbol'] == switch_info['swap']['symbol']]

# 获取现货的精度信息
exg_info_spot = get_exchange_info_spot(exchange, param={'symbol': switch_info['spot']['symbol']})
# print(exg_info_spot)
# exit()
# ===计算转仓币种相关信息
# 合约
switch_info['swap']['tickSize'] = exg_info_swap['tickSize'].iloc[0]
switch_info['swap']['minQty'] = exg_info_swap['minQty'].iloc[0]
# 现货
switch_info['spot']['tickSize'] = exg_info_spot['tickSize'].iloc[0]
switch_info['spot']['minQty'] = exg_info_spot['minQty'].iloc[0]


def loop(_switch, _exchange):
    global count
    if count >= count_limit:
        print('下单次数已经达到最大次数限制，下单终止。', datetime.datetime.now())
        exit()

    # 获取持仓信息，如果指定币种没有持仓，就停止程序
    pos = get_account(_exchange)[1]
    if _switch['swap']['symbol'] not in list(pos['symbol']):
        print('合约持仓为0，程序自动退出。', datetime.datetime.now())
        exit()
    _switch['swap']['pos'] = pos[pos['symbol'] == _switch['swap']['symbol']]['positionAmt'].iloc[0]  # 持仓的币的数量

    # 获取转仓币种的实时的价格数据
    swap_tick = get_tick_price(_exchange)
    spot_tick = get_tick_price_spot(_exchange)
    _switch['swap']['tick_price'] = swap_tick[swap_tick['symbol'] == _switch['swap']['symbol']]['tick_price'].iloc[0]
    _switch['spot']['tick_price'] = spot_tick[spot_tick['symbol'] == _switch['spot']['symbol']]['tick_price'].iloc[0]

    # 计算转仓币种的价差
    spread = _switch['spot']['tick_price'] / _switch['swap']['tick_price'] - 1
    print(
        '合约价格：%.4f，现货价格：%.4f，价差：%.4f%%' % (_switch['swap']['tick_price'], _switch['spot']['tick_price'], spread * 100))
    print(count)

    # 判断价差程度，根据价差选择是否转仓
    if spread > spread_limit:
        print('价差过大，暂不转仓。', datetime.datetime.now(), '\n')
    else:
        # 按照单次最大下单限制来计算本次的最大下单量
        _switch['nearby']['quantity'] = single_switch / _switch['nearby']['tick_price']
        _switch['forward']['quantity'] = single_switch / _switch['forward']['tick_price']
        if _switch['nearby']['quantity'] > _switch['nearby']['pos']:
            _switch['nearby']['quantity'] = _switch['nearby']['pos']
            _switch['forward']['quantity'] = _switch['nearby']['pos']
            print('我们最后一次移仓', datetime.datetime.now())

        # 计算下单价格 & 开仓方向
        _switch['swap']['price'] = _switch['swap']['tick_price'] * 0.99
        _switch['swap']['side'] = 'SELL'
        _switch['spot']['price'] = _switch['spot']['tick_price'] * 1.009
        _switch['spot']['side'] = 'BUY'

        # 根据最小下单量调整下单量，根据价格精度调整价格，并生成最终的下单信息
        order_info = create_order_info(_switch)
        print('下单信息：\n', order_info)

        # 下单
        swap_order_res = swap_order(exchange, order_info[order_info.index == 'swap'].copy())
        print(swap_order_res)
        spot_order_res = spot_order(exchange, order_info[order_info.index == 'spot'].copy())
        print(spot_order_res)
        count += 1

        # 下单之后，将下单的现货转移到U本位合约
        # print('开始将买入的现货转入')
        # trans_res = trans_spot2swap(exchange, param={'type': 'MAIN_UMFUTURE', 'asset': _switch['spot']['symbol'],
        #                                        'amount': order_info.loc['spot', 'quantity']})
        # print(trans_res)



while True:
    loop(switch_info, exchange)
    time.sleep(run_interval)

# while True:
#     try:
#         loop(switch_info, exchange)
#         time.sleep(run_interval)
#     except Exception as e:
#         print('系统出错，10s之后重新运行，出错原因：' + str(e))
#         print(e)
#         time.sleep(run_interval)
