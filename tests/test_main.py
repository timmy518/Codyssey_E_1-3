"""(보충) main.py 단위 테스트

미션 필수 항목은 아니고, 재현성 조건(예시 입력, 오류 입력, 케이스 단위 FAIL,
data.json 결과와 총합 일치)을 확인하려고 추가했다. 표준 라이브러리 unittest 만 쓴다.

실행: python -m unittest discover -s tests
"""

import io
import json
import os
import subprocess
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


def run_json_text(text):
    """text 를 임시 data.json 으로 저장하고 모드 2 를 실행한 뒤 화면 출력을 돌려준다."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "data.json")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        out = io.StringIO()
        with redirect_stdout(out):
            main.run_json_mode(path)
    return out.getvalue()


def run_json(data):
    """data 를 JSON 으로 바꿔 모드 2 를 실행한 뒤 화면 출력을 돌려준다."""
    return run_json_text(json.dumps(data))


def filters_5():
    """정상인 size_5 필터 묶음 (data.json 의 키 표기 그대로)."""
    return {"size_5": {"cross": main.generate_cross(5), "x": main.generate_x(5)}}


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
        self.assertIsNone(main.shape_of([1, 2, 3]))
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

    def test_exact_epsilon_difference_is_not_a_tie(self):
        # 차이가 EPSILON 과 같으면 '<' 비교라서 동점이 아니고, 그보다 작으면 동점이다.
        self.assertEqual(abs(0.0 - main.EPSILON), main.EPSILON)
        self.assertEqual(main.judge(0.0, main.EPSILON, "A", "B", "판정 불가"), "B")
        self.assertEqual(main.judge(0.0, main.EPSILON / 2, "A", "B", "판정 불가"), "판정 불가")

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

    def test_wrong_decision_fails(self):
        data = {"filters": filters_5(),
                "patterns": {"size_5_1": {"input": main.generate_cross(5), "expected": "x"}}}
        out = run_json(data)
        self.assertIn("판정: Cross | expected: X | FAIL (판정(Cross)과 expected(X) 불일치)", out)
        self.assertIn("- size_5_1: 판정(Cross)과 expected(X) 불일치", out)

    def test_zero_failures_summary(self):
        data = {"filters": filters_5(),
                "patterns": {"size_5_1": {"input": main.generate_x(5), "expected": "x"},
                             "size_5_2": {"input": main.generate_cross(5), "expected": "+"}}}
        out = run_json(data)
        self.assertIn("통과: 2개", out)
        self.assertIn("실패: 0개", out)
        self.assertIn("실패 케이스: 없음", out)

    def test_filter_problems_are_reported(self):
        data = {
            "filters": {
                **filters_5(),
                "big_5": {"cross": main.generate_cross(5), "x": main.generate_x(5)},
                "size_7": [1, 2],
                "size_9": {"cross": main.generate_cross(9), "o": main.generate_x(9)},
                "size_11": {"cross": main.generate_cross(11), "x": main.generate_x(10)},
                "size_13": {"cross": main.generate_cross(13)},
            },
            "patterns": {
                "size_5_1": {"input": [["a"] * 5 for _ in range(5)], "expected": "+"},
                "size_11_1": {"input": main.generate_cross(11), "expected": "+"},
            },
        }
        out = run_json(data)
        self.assertIn("size_5 필터 로드 완료 (Cross, X)", out)
        self.assertIn("big_5 필터 로드 실패: 키 형식 오류 (size_{N} 형태가 아닙니다)", out)
        self.assertIn("size_7 필터 로드 실패: 필터 묶음이 객체가 아닙니다", out)
        self.assertIn("size_9 필터 로드 실패: 알 수 없는 필터 키 'o'", out)
        self.assertIn("size_11 필터 로드 실패: X 필터 크기 불일치 (10×10, 필요 11×11)", out)
        self.assertIn("size_13 필터 로드 실패: X 필터가 없습니다", out)
        self.assertIn("- size_5_1: 패턴이 숫자로 된 2차원 배열이 아닙니다", out)
        self.assertIn("- size_11_1: size_11 필터를 쓸 수 없습니다: X 필터 크기 불일치 (10×10, 필요 11×11)", out)

    def test_file_level_problems_do_not_crash(self):
        self.assertIn("data.json 을 읽을 수 없습니다", run_json_text("{ broken"))
        self.assertIn("스키마 오류: data.json 의 최상위가 객체가 아닙니다.", run_json([1, 2, 3]))
        out = run_json({"patterns": {"size_5_1": {"input": main.generate_x(5), "expected": "x"}}})
        self.assertIn("스키마 오류: filters 항목이 없거나 형식이 다릅니다.", out)
        self.assertIn("- size_5_1: size_5 필터가 없습니다", out)
        out = run_json({"filters": filters_5()})
        self.assertIn("스키마 오류: patterns 항목이 없거나 형식이 다릅니다.", out)
        self.assertIn("총 테스트: 0개", out)

    def test_performance_table_lists_each_size(self):
        data = {"filters": filters_5(),
                "patterns": {"size_5_1": {"input": main.generate_x(5), "expected": "x"}}}
        out = run_json(data)
        for size in (3, 5, 13, 25):
            self.assertRegex(out, rf"(?m)^{size}×{size}\s+\d+\.\d{{4}}\s+{size * size}$")
        self.assertIn("[보너스] 1차원 배열 최적화 전/후 비교 (평균/10회)", out)


class GeneratorModeTest(unittest.TestCase):
    def test_size_input_is_validated(self):
        # 짝수, 위첨자 숫자(예전에 멈추던 입력), 3 미만, 문자 다음에 정상 값
        out = run_with_input(main.run_generator_mode, ["4", "²", "1", "abc", "5"])
        self.assertEqual(out.count("입력 형식 오류: 3 이상의 홀수를 입력하세요."), 4)
        self.assertIn("Cross 패턴 (5×5)", out)

    def test_generated_patterns_are_judged(self):
        out = run_with_input(main.run_generator_mode, ["3"])
        self.assertIn("Cross 패턴 입력 -> A 점수: 5.0, B 점수: 1.0, 판정: A", out)
        self.assertIn("X 패턴 입력 -> A 점수: 1.0, B 점수: 5.0, 판정: B", out)
        self.assertIn("[보너스] 1차원 배열 최적화 전/후 비교", out)


class MenuTest(unittest.TestCase):
    def test_invalid_choice_is_asked_again(self):
        out = run_with_input(main.main, ["9", "", "3", "3"])
        self.assertEqual(out.count("1, 2, 3 중 하나를 입력하세요."), 2)
        self.assertIn("# [1] 패턴 생성", out)

    def test_each_choice_runs_its_mode(self):
        self.assertIn("# [3] MAC 결과", run_with_input(main.main, ["1"] + EXAMPLE_INPUT))
        self.assertIn("총 테스트: 6개", run_with_input(main.main, ["2"]))

    def test_end_of_input_exits_cleanly(self):
        # main.py 를 직접 실행하고 입력을 도중에 끊는다.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, os.path.join(ROOT, "main.py")], input="1\n0 1 0\n",
                                capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        self.assertEqual(result.returncode, 0)
        self.assertIn("입력이 끝나 프로그램을 종료합니다.", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


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
