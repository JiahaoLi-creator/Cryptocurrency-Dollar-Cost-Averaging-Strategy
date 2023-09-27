import ccxt
from BL定投脚本.program.functions import *
from view_position import run_check

exchange = ccxt.binance(api_config)

# 检查多空是否平衡，是否达 到最小下单量55555t7
check_order(exchange)
print(long_dict)
print(short_dict)

# 创建下单信息
order_df = create_order_info(exchange)
print('下单信息：\n', order_df)
# exit() # 注释掉这里就会下单
# 在下单信息里加入时间戳
order_df['timeStamp'] = str(int(time.time() * 1000))

# 将下单信息从df转为dict格式
order_info = order_df.to_dict('records')

# 批量下单，每 5 个订单打包执行
for j in range(0, len(order_info), 5):
    oder_res = rest_api_req(
        lambda: exchange.fapiPrivate_post_batchorders({'batchOrders': json.dumps(order_info[j: j + 5])}),
        ts=exchange.rateLimit / 1000, )
    print(oder_res)

run_check()
