from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def max_profit_single(prices):
    """买卖股票最佳时机"""
    if not prices:
        tracer.finish(line=1)
        return 0

    tracer.init_array(prices, line=5)
    min_price = prices[0]
    max_profit = 0

    for i, price in enumerate(prices):
        tracer.move_pointer({"i": i}, line=10)
        tracer.compare(i, 0, line=11)
        if price < min_price:
            min_price = price
        else:
            profit = price - min_price
            if profit > max_profit:
                max_profit = profit

    tracer.finish(line=20)
    return max_profit
