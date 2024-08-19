from .imports import *
import pytest
import json
import csv
import time

from .paths import FileJester, MultiFileJester, AutoFileJester
# from .progress_bar import ProgressBar


@pytest.fixture
def complex_file_structure(tmp_path):
	# Create nested directories
	dir1 = tmp_path / "dir1"
	dir1.mkdir()

	dir2 = tmp_path / "dir1" / "dir2"
	dir2.mkdir()

	dir3 = tmp_path / "dir1" / "dir2" / "dir3"
	dir3.mkdir()

	# Create JSON files
	json_file_1 = tmp_path / "dir1" / "file1.json"
	json_file_2 = tmp_path / "dir1" / "dir2" / "file2.json"
	json_file_3 = tmp_path / "dir1" / "dir2" / "other-file.json"

	data = {"key": "value"}

	with open(json_file_1, "w") as f:
		json.dump(data, f)

	with open(json_file_2, "w") as f:
		json.dump(data, f)

	with open(json_file_3, "w") as f:
		json.dump(data, f)

	# Create CSV files
	csv_file_1 = tmp_path / "dir1" / "file1.csv"
	csv_file_2 = tmp_path / "dir1" / "dir2" / "dir3" / "file3.csv"

	with open(csv_file_1, "w", newline="") as f:
		writer = csv.writer(f)
		writer.writerow(["column1", "column2"])
		writer.writerow(["value1", "value2"])

	with open(csv_file_2, "w", newline="") as f:
		writer = csv.writer(f)
		writer.writerow(["column1", "column2"])
		writer.writerow(["value3", "value4"])

	# Return the path to the temporary directory
	return tmp_path



def test_jester(complex_file_structure):
	base_path = complex_file_structure

	pattern = base_path / "**" / "*.json"

	jester = FileJester(str(pattern))

	assert jester.remaining == 3

	generated = list(jester)

	assert jester.remaining == 0

	paths = [p.relative_to(jester.root) for p in generated]

	print(jester.root)
	print(paths)



def test_auto_jester(complex_file_structure):
	base_path = complex_file_structure

	jester = AutoFileJester(base_path, 'json')

	assert jester.remaining == 3

	generated = list(jester)

	assert jester.remaining == 0

	paths = [p.relative_to(jester.root) for p in generated]

	print(jester.root)
	print(paths)

	pass


def test_pbar():
	pbar = ProgressBar()
	ls = []
	for x in pbar.push(4, seeder=lambda x: 'abcde', scribe=lambda x: f'Processing {x + 1}'):
		time.sleep(0.2)
		ls.append(x)
	print(ls)












