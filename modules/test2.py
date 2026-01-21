# import os
# import nbformat
# from nbconvert import PythonExporter
#
# # 目标目录
# path = r"D:\03.大屏计算开发代码V1.0-20250910"
#
# # 遍历目标目录下的所有 ipynb 文件
# for file in os.listdir(path):
#     if file.endswith(".ipynb"):
#         ipynb_file = os.path.join(path, file)
#         with open(ipynb_file, "r", encoding="utf-8") as f:
#             nb = nbformat.read(f, as_version=4)
#         exporter = PythonExporter()
#         source, _ = exporter.from_notebook_node(nb)
#
#         py_file = os.path.splitext(ipynb_file)[0] + ".py"
#         with open(py_file, "w", encoding="utf-8") as f:
#             f.write(source)
#         print(f"已转换: {ipynb_file} -> {py_file}")
