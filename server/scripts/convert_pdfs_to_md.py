import os
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def convert_single_pdf(pdf_file: Path):
    """
    单个 PDF 转换任务
    """
    output_dir = pdf_file.parent
    
    # 构建 mineru 的转换命令
    cmd = [
        "uv", "run", "mineru",
        "-p", str(pdf_file),
        "-o", str(output_dir)
    ]
    
    try:
        # 执行转换命令
        # stdout=subprocess.PIPE, stderr=subprocess.PIPE 用来捕获输出，避免多线程时控制台日志混乱
        process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, pdf_file.name, None
    except subprocess.CalledProcessError as e:
        # 返回失败状态及错误信息（可以打印 e.stderr 以获取具体报错）
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return False, pdf_file.name, error_msg
    except Exception as e:
        return False, pdf_file.name, str(e)

def convert_all_pdfs(data_dir="data", max_workers=3):
    """
    多线程转换目录下所有的 PDF 文件
    """
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / data_dir

    pdf_files = list(data_path.rglob("*.pdf"))
    if not pdf_files:
        print(f"在 {data_path} 下未找到任何 PDF 文件。")
        return

    print(f"📦 找到 {len(pdf_files)} 个 PDF 文件，准备使用 {max_workers} 个并发线程开始转换...")
    print("⚠️ 注意: mineru 解析可能会消耗较大的 CPU/内存，如果电脑卡顿，请尝试调小 max_workers 的数量。")

    success_count = 0
    fail_count = 0

    # 使用线程池并发执行转换任务
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有 PDF 转换任务到线程池
        futures = {executor.submit(convert_single_pdf, pdf_file): pdf_file for pdf_file in pdf_files}
        
        # 实时获取完成的任务结果
        for future in as_completed(futures):
            success, filename, error = future.result()
            if success:
                print(f"✅ 转换成功: {filename}")
                success_count += 1
            else:
                print(f"❌ 转换失败: {filename} \n   -> 原因: {error[:200]}...") # 截断错误信息避免过长
                fail_count += 1

    print(f"\n🎉 转换任务全部结束！总计成功: {success_count} 个，失败: {fail_count} 个。")

if __name__ == "__main__":
    # 获取系统 CPU 核心数，保守起见默认使用不超过 CPU 核心数一半的线程，或者你可以手动写死比如 max_workers=2
    cpu_count = os.cpu_count() or 4
    suggested_workers = max(1, cpu_count // 2)
    
    # 鉴于 mineru 比较吃资源，这里设定一个默认的安全上限 3，如果你的电脑性能很强可以往上调
    max_concurrency = min(suggested_workers, 3) 
    
    convert_all_pdfs(max_workers=max_concurrency)
