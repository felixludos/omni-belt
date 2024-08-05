from typing import Union, Iterable, Tuple, Optional, List
import sys, os
import re
from pathlib import Path
import json, yaml
from collections import UserList

# import h5py as hdf
# try:
#     from datasets import load_dataset
# except ImportError:
#     load_dataset = None



def where_am_i():
    '''
    Returns a string indicating the current environment, allowing to differentiate among, for example:
    - 'jupyter': Jupyter notebook or JupyterLab
    - 'colab': Google Colab
    - 'cluster': Running on a cluster (defined by the presence of the 'JOB_ID' environment variable)
    - 'ci': Continuous integration environment
    - 'repl': Python REPL
    - 'pycharm': PyCharm IDE
    - 'vscode': Visual Studio Code
    - 'script': Running as a script
    '''
    loc = os.environ.get('WHEREAMI', None)
    if loc is not None:
        return loc

    if os.environ.get('JOB_ID', None) is not None:
        return 'cluster'
    elif 'COLAB_GPU' in os.environ:
        return "colab"
    elif any(ci in os.environ for ci in ['JENKINS_HOME', 'GITHUB_ACTIONS', 'GITLAB_CI', 'TRAVIS']):
        return "ci"
    # elif 'LAMBDA_RUNTIME_DIR' in os.environ:
    #     return "aws_lambda"
    # elif 'SPYDER' in sys.modules:
    #     return "spyder"
    # elif 'jupyterlab' in sys.modules:
    #     return "jupyterLab"
    elif hasattr(sys, 'ps1'):
        return 'repl'
    elif 'pydevd' in sys.modules:
        return 'pycharm'
    elif 'ptvsd' in sys.modules or 'debugpy' in sys.modules:
        return "vscode"
    
    try:
        from IPython import get_ipython
        if 'IPKernelApp' in get_ipython().config: 
            return 'jupyter'
    except:
        pass
    
    return 'script'


def where_could_i_be():
    '''
    Returns a list of possible environments where the code could be running, allowing to differentiate among, for example:
    '''
    return ['jupyter', 'colab', 'cluster', 'ci', 
            # 'aws_lambda', 'spyder', 'jupyterLab', 
            'repl', 'pycharm', 'vscode', 'script']




class FileJester:
    def __init__(self, src: Union[Path, str], *, lazy: bool = False):
        if lazy:
            raise NotImplementedError("Lazy loading is not yet implemented")
        if isinstance(src, str):
            src = Path(src)
        self.src = src
        
    
    def _extract_root(self, path: Path):
        path = path.expanduser().resolve()
        return path if path.exists() else self._extract_root(path.parent)


    def analyze(self, src: Path, *, includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
        if src.exists():
            if src.is_dir():
                raise ValueError("The 'src' parameter must be a file or pattern, not a directory")
            else:
                return src.parent, 1, src
        
        root = self._extract_root(src)
        pattern = src.relative_to(root)
        children = list(root.glob(str(pattern)))
        if includeupper:
            base = pattern.parent / pattern.stem
            ext = pattern.suffix
            children.extend(root.glob(base.with_suffix(ext.upper())))
            children = sorted(children)
        
        if len(children) == 0:
            raise FileNotFoundError(f"'{pattern}' in {root}")
        if len(children) == 1:
            return root, 1, children[0]
        return root, len(children), children

    
    def peek(self):
        raise NotImplemented


    def __iter__(self):
        return self.flow()


    def __len__(self):
        raise NotImplemented

    
    def flow(self):
        raise NotImplemented

    pass



class AutoFileJester(FileJester):
    def __init__(self, src: Union[Path, str], ext: str = None, 
                 *, recursive: bool = True, lazy: bool = False, **kwargs):
        super().__init__(src, lazy=lazy, **kwargs)
        self.ext = ext
        self.recursive = recursive


    def analyze(self, src: Path, ext: Optional[str] = None, *, 
                recursive: bool = True, includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
        if src.is_dir():
            if ext is None:
                raise ValueError("The 'ext' parameter must be provided when the source is a directory")
            src = src / f'{"**/" if recursive else ""}*.{ext}'
        return super().analyze(src, includeupper=includeupper)



class MultiFileJester(FileJester):
    def __init__(self, src: Union[Path, str, Iterable[Union[Path, str]]], *, lazy: bool = False, **kwargs):
        if isinstance(src, (Path, str)):
            src = [src]
        if not isinstance(src, Path):
            src = [Path(s) for s in src]
        super().__init__(src, lazy=lazy)
    

    def include(self, src: Union[Path, str, Iterable[Union[Path, str]]]):
        if isinstance(src, str):
            src = Path(src)
        if not isinstance(src, Path):
            src = [Path(s) for s in src]
        self.src.extend(src)


    def analyze(self, src: Union[Path, Iterable[Path]], *, 
                includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
        if isinstance(src, Path):
            return super().analyze(src, includeupper=includeupper)
        
        assert isinstance(src, Iterable), "The 'src' parameter must be a Path, str, or Iterable of Paths or strings"
        roots, counts, branches = zip(*[self.analyze(branch, includeupper=includeupper) for branch in src])
        root = min(roots, key=lambda r: len(str(r)))
        return root, sum(counts), list(branches)
        


