"""一次跑完三個實驗，結果存成 experiments/results_exp1~3.csv。

執行（在 noshow_system 資料夾）：python -m experiments.run_all
約需數分鐘（退化 BST、全部資料的陣列操作比較慢）。
"""

from experiments import exp1_search, exp2_topk, exp3_delete


def main():
    exp1_search.main()
    exp2_topk.main()
    exp3_delete.main()


if __name__ == "__main__":
    main()
