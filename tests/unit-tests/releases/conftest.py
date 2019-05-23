import tarfile
import zipfile

import pytest


@pytest.fixture
def single_file_tar(tmp_path):
    with tarfile.open(str(tmp_path.joinpath('single-file.tar.gz')), 'x:gz') as archive:
        path = tmp_path.joinpath(f'file-in-single-tar.txt')
        path.touch()
        archive.add(path)
    return archive


@pytest.fixture
def multi_file_tar(tmp_path):
    """A `.tar.gz` archive.

    Contains the following empty files:

        file-in-tar0.txt
        file-in-tar1.txt
        file-in-tar2.txt
        file-in-tar3.txt
        file-in-tar4.txt
    """
    with tarfile.open(tmp_path.joinpath('multi-file.tar.gz'), 'x:gz') as archive:
        for i in range(5):
            path = tmp_path.joinpath(f'file-in-tar{i}.txt')
            path.touch()
            archive.add(path)
    return archive


@pytest.fixture
def single_file_zip(tmp_path):
    with zipfile.ZipFile(tmp_path.joinpath('single-file.zip'), 'x') as archive:
        path = tmp_path.joinpath(f'file-in-single-zip.txt')
        path.touch()
        archive.write(path)
    return archive


@pytest.fixture
def multi_file_zip(tmp_path):
    """A `.zip` archive.

    Contains the following empty files:

        file-in-zip0.txt
        file-in-zip1.txt
        file-in-zip2.txt
        file-in-zip3.txt
        file-in-zip4.txt

    """
    with zipfile.ZipFile(tmp_path.joinpath('multi-file.zip'), 'x') as archive:
        for i in range(5):
            path = tmp_path.joinpath(f'file-in-zip{i}.txt')
            path.touch()
            archive.write(path)
    return archive
