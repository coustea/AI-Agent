def max_profit_single(prices):
    min_price = float('inf')
    max_profit = 0
    for p in prices:
        min_price = min(min_price, p)
        max_profit = max(max_profit, p - min_price)
    return max_profit

def max_profit_unlimited(prices):
    profit = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            profit += prices[i] - prices[i - 1]
    return profit

def max_profit_two_transactions(prices):
    n = len(prices)
    if n < 2:
        return 0
    left_profit = [0] * n
    min_price = prices[0]
    for i in range(1, n):
        left_profit[i] = max(left_profit[i - 1], prices[i] - min_price)
        min_price = min(min_price, prices[i])
    right_profit = [0] * n
    max_price = prices[-1]
    for i in range(n - 2, -1, -1):
        right_profit[i] = max(right_profit[i + 1], max_price - prices[i])
        max_price = max(max_price, prices[i])
    return max(left_profit[i] + right_profit[i] for i in range(n))

def max_profit_with_cooldown(prices):
    n = len(prices)
    if n < 2:
        return 0
    hold = -prices[0]
    sold = 0
    rest = 0
    for i in range(1, n):
        prev_sold = sold
        hold = max(hold, rest - prices[i])
        sold = hold + prices[i]
        rest = max(rest, prev_sold)
    return max(sold, rest)

datasets = [
    [7, 1, 5, 3, 6, 4],
    [7, 6, 4, 3, 1],
    [1, 2, 3, 4, 5],
    [3, 3, 5, 0, 0, 3, 1, 4],
]

for prices in datasets:
    r1 = max_profit_single(prices)
    r2 = max_profit_unlimited(prices)
    r3 = max_profit_two_transactions(prices)
    r4 = max_profit_with_cooldown(prices)
