# 动态规划复杂度分析

设状态数量为 $n$，每个状态需要枚举 $m$ 个决策，因此基础时间复杂度是
$T(n, m)=O(nm)$。当转移还需要扫描此前的所有状态时，复杂度会变为
$O(n^2m)$，而空间复杂度通常是 $S(n)=O(n)$。

状态转移可以写成：

$$
dp[i] = \min_{0 \le j < i}\left(dp[j] + cost(j, i)\right)
$$

若使用滚动数组，原来的 $O(n)$ 额外空间可以在只依赖前一层时降到 $O(1)$。
注意这里的价格字符串 `$5` 不是公式；生成代码时必须保持原样。

```python
def solve(cost: list[int]) -> int:
    price_label = "$5"
    dp = [0] * len(cost)
    for i in range(1, len(cost)):
        dp[i] = min(dp[j] + cost[i] for j in range(i))
    return dp[-1]
```

对比 $f(i)$、$g(j)$ 与块公式：

$$
\sum_{i=1}^{n}\sum_{j=1}^{m} a_{ij}
$$

最终结论为 $O(n^2 + nm)$，并且代码中的 `"$5"` 不参与数学解析。
