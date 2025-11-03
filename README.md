# hqg-algorithms


## Run locally
In project root:

```shell
python3 -m pip install --upgrade pip setuptools wheel
pip install -e .
```

Test in python shell:
```py
from hqg_algorithms import Strategy
s = Strategy("demo")
print(s.name)
```

## Publish to PyPI
### 1. Get API key for HQG account

### 2. Build the package (in project root):
```shell
pip install build
python3 -m build
```

This creates:
```
dist/
├── hqg_algorithms-0.1.0.tar.gz
└── hqg_algorithms-0.1.0-py3-none-any.whl
```

### 3. Upload to PyPI with twine:
```shell
pip install twine
twine upload dist/* 
```

When prompted, use:
```shell
username: __token__
password: pypi-<your-token>
```

### 4. Verify:
Visit [https://pypi.org/project/hqg-algorithms/](https://pypi.org/project/hqg-algorithms/)
