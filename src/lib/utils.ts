import type { ClassValue } from "clsx" // 导入 clsx 类值类型
import { clsx } from "clsx" // 导入类名拼接工具
import { twMerge } from "tailwind-merge" // 导入 Tailwind 类名去重合并工具

export function cn(...inputs: ClassValue[]) { // 合并 Tailwind CSS 类名（去重 + 覆盖冲突）
  return twMerge(clsx(inputs))
}
