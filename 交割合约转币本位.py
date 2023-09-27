import time
import pandas as pd
from program.function import *
import ccxt
import datetime

# 创建交易所对象
exchange = ccxt.binance(api_config)
count = 0  # 下单次数
# ===计算转仓币种最小下单量等信息
# 获取合约的精度信息
exg_info_swap = get_exchange_info(exchange)
exg_info_swap = exg_info_swap[exg_info_swap['symbol'] == switch_info['swap']['symbol']]

# 获取币本位合约的精度信息
exg_info_swap_coin = get_exchange_info_swap_coin(exchange, symbol=switch_info['swap_coin']['symbol'])
# print(exg_info_swap_coin)
# exit()
# ===计算转仓币种相关信息
# 合约
switch_info['swap']['tickSize'] = exg_info_swap['tickSize'].iloc[0]
switch_info['swap']['minQty'] = exg_info_swap['minQty'].iloc[0]
# 币本位合约
switch_info['swap_coin']['tickSize'] = exg_info_swap_coin['tickSize'].iloc[0]
switch_info['swap_coin']['minQty'] = exg_info_swap_coin['minQty'].iloc[0]
switch_info['swap_coin']['contractSize'] = exg_info_swap_coin['contractSize'].iloc[0]  # 当前币种的合约面值，币本位下单按照合约张数计算


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
    swap_coin_tick = get_tick_price_swap_coin(_exchange)
    _switch['swap']['tick_price'] = swap_tick[swap_tick['symbol'] == _switch['swap']['symbol']]['tick_price'].iloc[0]
    _switch['swap_coin']['tick_price'] = swap_coin_tick[swap_coin_tick['symbol'] == _switch['swap_coin']['symbol']]['tick_price'].iloc[0]

    # 计算转仓币种的价差
    spread = _switch['swap_coin']['tick_price'] / _switch['swap']['tick_price'] - 1
    print('合约价格：%.4f，币本位价格：%.4f，价差：%.4f%%' % (_switch['swap']['tick_price'], _switch['swap_coin']['tick_price'], spread * 100))
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
        _switch['swap_coin']['price'] = _switch['swap_coin']['tick_price'] * 1.009
        _switch['swap_coin']['side'] = 'BUY'

        # 根据最小下单量调整下单量，根据价格精度调整价格，并生成最终的下单信息
        order_info = create_order_info(_switch)
        print('下单信息：\n', order_info)

        # 下单
        swap_order_res = swap_order(exchange, order_info[order_info.index == 'swap'].copy())
        print(swap_order_res)
        swap_coin_order_res = swap_coin_order(exchange, order_info[order_info.index == 'swap_coin'].copy())
        print(swap_coin_order_res)
        count += 1


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
