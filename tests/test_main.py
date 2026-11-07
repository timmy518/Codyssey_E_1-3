"""(보충) main.py 단위 테스트

미션 필수 항목은 아니고, 재현성 조건(예시 입력, 오류 입력, 케이스 단위 FAIL,
data.json 결과와 총합 일치)을 확인하려고 추가했다. 표준 라이브러리 unittest 만 쓴다.

실행: python -m unittest discover -s tests
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import main  # noqa: E402

CROSS3 = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
X3 = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
EXAMPLE_INPUT = ["0 1 0", "1 1 1", "0 1 0",   # 필터 A (십자가)
                 "1 0 1", "0 1 0", "1 0 1",   # 필터 B (X)
                 "1 0 1", "0 1 0", "1 0 1"]   # 패턴 (X)


def run_with_input(func, lines, *args):
    """input() 에 lines 를 차례로 넣고 func 를 실행한 뒤 화면 출력을 돌려준다."""
    out = io.StringIO()
    with mock.patch("builtins.input", side_effect=list(lines)), redirect_stdout(out):
        func(*args)
    return out.getvalue()


def run_json(data):
    """data 를 임시 data.json 으로 저장하고 모드 2 를 실행한 뒤 화면 출력을 돌려준다."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "data.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file)
        out = io.StringIO()
        with redirect_stdout(out):
            main.run_json_mode(path)
    return out.getvalue()


class DataStructureTest(unittest.TestCase):
    def test_store_and_read_each_size(self):
        for size in (3, 5, 13, 25):
            matrix = main.create_matrix(size)
            self.assertEqual(main.shape_of(matrix), (size, size))
            main.set_value(matrix, size - 1, 0, 2.5)
            self.assertEqual(main.get_value(matrix, size - 1, 0), 2.5)

    def test_shape_of_rejects_bad_arrays(self):
        self.assertIsNone(main.shape_of([[1, 2], [3]]))
        self.assertIsNone(main.shape_of([[1, "a"], [3, 4]]))
        self.assertIsNone(main.shape_of([[True, 0], [0, 1]]))
        self.assertIsNone(main.shape_of("not a list"))
        self.assertEqual(main.shape_of([[1, 2, 3], [4, 5, 6]]), (2, 3))


class MacTest(unittest.TestCase):
    def test_mission_example_scores(self):
        self.assertEqual(main.mac(CROSS3, CROSS3), 5.0)
        self.assertEqual(main.mac(CROSS3, X3), 1.0)

    def test_flat_version_gives_same_score(self):
        for size in (3, 5, 13, 25):
            pattern, filt = main.generate_cross(size), main.generate_x(size)
            flat = main.mac_flat(main.flatten(pattern), main.flatten(filt))
            self.assertEqual(main.mac(pattern, filt), flat)


class JudgeTest(unittest.TestCase):
    def test_bigger_score_wins(self):
        self.assertEqual(main.judge(5.0, 1.0, "A", "B", "판정 불가"), "A")
        self.assertEqual(main.judge(1.0, 5.0, "A", "B", "판정 불가"), "B")

    def test_float_error_is_a_tie(self):
        self.assertNotEqual(0.1 * 3, 0.3)
        self.assertEqual(main.judge(0.1 * 3, 0.3, "A", "B", "판정 불가"), "판정 불가")
        self.assertEqual(main.judge(0.9, 0.8999999999999999, main.CROSS, main.X, main.UNDECIDED),
                         main.UNDECIDED)


class LabelTest(unittest.TestCase):
    def test_known_labels(self):
        cases = {"+": "Cross", "cross": "Cross", " Cross ": "Cross", "x": "X", "X": "X"}
        for raw, label in cases.items():
            self.assertEqual(main.normalize_label(raw), label)

    def test_unknown_labels(self):
        for raw in ("o", "", None, 1):
            self.assertIsNone(main.normalize_label(raw))


class GeneratorTest(unittest.TestCase):
    def test_same_as_mission_example(self):
        self.assertEqual(main.generate_cross(3), CROSS3)
        self.assertEqual(main.generate_x(3), X3)

    def test_scores_for_generated_sizes(self):
        for size in (5, 13, 25):
            cross, x_pattern = main.generate_cross(size), main.generate_x(size)
            self.assertEqual(main.mac(cross, cross), 2 * size - 1)
            self.assertEqual(main.mac(cross, x_pattern), 1.0)


class UserModeTest(unittest.TestCase):
    def test_mission_example(self):
        out = run_with_input(main.run_user_mode, EXAMPLE_INPUT)
        self.assertIn("A 점수: 1.0", out)
        self.assertIn("B 점수: 5.0", out)
        self.assertIn("판정: B", out)
        self.assertIn("연산 시간(평균/10회)", out)
        self.assertIn("3×3", out)

    def test_bad_rows_are_entered_again(self):
        lines = ["0 1", "0 1 0", "a b c", "1 1 1", "0 1 0 1", "0 1 0"] + EXAMPLE_INPUT[3:]
        out = run_with_input(main.run_user_mode, lines)
        self.assertEqual(out.count("입력 형식 오류"), 3)
        self.assertIn("판정: B", out)

    def test_tie_is_undecided(self):
        lines = EXAMPLE_INPUT[:6] + ["0.3 0.3 0.3"] * 3
        out = run_with_input(main.run_user_mode, lines)
        self.assertIn("판정: 판정 불가", out)


class JsonModeTest(unittest.TestCase):
    def test_problem_cases_fail_without_stopping(self):
        data = {
            "filters": {"size_5": {"cross": main.generate_cross(5), "x": main.generate_x(5)}},
            "patterns": {
                "size_5_1": {"input": main.generate_x(5), "expected": "x"},
                "size_5_2": {"input": main.generate_cross(5), "expected": "+"},
                "size_5_3": {"input": main.generate_cross(3), "expected": "+"},
                "size_13_1": {"input": main.generate_cross(13), "expected": "+"},
                "size_5_4": {"input": main.generate_cross(5), "expected": "o"},
                "size_5_5": {"input": main.generate_cross(5)},
                "wrong_key": {"input": main.generate_cross(5), "expected": "+"},
            },
        }
        out = run_json(data)
        self.assertIn("size_5 필터 로드 완료 (Cross, X)", out)
        self.assertIn("총 테스트: 7개", out)
        self.assertIn("통과: 2개", out)
        self.assertIn("실패: 5개", out)
        self.assertIn("- size_5_3: 크기 불일치 (패턴 3×3, 필터 5×5)", out)
        self.assertIn("- size_13_1: size_13 필터가 없습니다", out)

    def test_tie_case_fails_by_rule(self):
        data = {
            "filters": {"size_5": {"cross": main.generate_cross(5), "x": main.generate_x(5)}},
            "patterns": {"size_5_1": {"input": [[0.1] * 5 for _ in range(5)], "expected": "x"}},
        }
        out = run_json(data)
        self.assertIn("판정: UNDECIDED | expected: X | FAIL", out)

    def test_missing_file_does_not_crash(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main.run_json_mode(os.path.join(ROOT, "no_such_file.json"))
        self.assertIn("data.json 파일을 찾을 수 없습니다", out.getvalue())


class RealDataTest(unittest.TestCase):
    """저장소의 data.json 결과가 README 결과 리포트와 같은지 확인한다."""

    def test_totals_match_case_results(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main.run_json_mode(main.DATA_FILE)
        text = out.getvalue()
        self.assertIn("총 테스트: 6개", text)
        self.assertIn("통과: 3개", text)
        self.assertIn("실패: 3개", text)
        self.assertEqual(text.count("| PASS"), 3)
        for key in ("size_5_1", "size_13_2", "size_25_1"):
            self.assertIn(f"- {key}: 동점(UNDECIDED) 처리 규칙", text)


if __name__ == "__main__":
    unittest.main()
