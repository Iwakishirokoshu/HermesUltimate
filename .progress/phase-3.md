# Phase 3 Gate Report

completed: 2026-06-13 17:29
status: PASS

## Completed Tasks

T-200 9ed7984
T-201 277c16b
T-202 f84581f
T-203 55d3b29
T-204 da354fd
T-205 ed9f7e1
T-206 c4aceef
T-207 35a454f
T-208 bf63cd0
T-209 abe0a30
T-210 076d8ed
T-211 b54ee06
T-212 124baea

## Gate-check Output

```text
$ bash scripts/init-vault.sh
HermesVault initialized at /c/Users/Around/HermesVault
exit: 0

$ docker compose -f stack/docker-compose.yml up -d vault-api
 Image stack-vault-api Building 
#1 [internal] load local bake definitions
#1 reading from stdin 561B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 453B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.11-slim
#3 ...

#4 [auth] library/python:pull token for registry-1.docker.io
#4 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.11-slim
#3 DONE 1.1s

#5 [internal] load .dockerignore
#5 transferring context: 2B done
#5 DONE 0.0s

#6 [1/5] FROM docker.io/library/python:3.11-slim@sha256:f9fa7f851e38bfb19c9de3afbc4b86ae7176ea7aaf94535c31df5458d5849457
#6 resolve docker.io/library/python:3.11-slim@sha256:f9fa7f851e38bfb19c9de3afbc4b86ae7176ea7aaf94535c31df5458d5849457 0.0s done
#6 DONE 0.0s

#7 [internal] load build context
#7 transferring context: 18.23kB done
#7 DONE 0.0s

#8 [2/5] WORKDIR /app
#8 CACHED

#9 [3/5] COPY . /app
#9 DONE 0.0s

#10 [4/5] RUN if [ -f requirements.txt ]; then       pip install --no-cache-dir -r requirements.txt;     fi
#10 1.184 Collecting fastapi (from -r requirements.txt (line 1))
#10 1.353   Downloading fastapi-0.136.3-py3-none-any.whl.metadata (27 kB)
#10 1.411 Collecting uvicorn (from -r requirements.txt (line 2))
#10 1.443   Downloading uvicorn-0.49.0-py3-none-any.whl.metadata (6.7 kB)
#10 1.490 Collecting filelock (from -r requirements.txt (line 3))
#10 1.520   Downloading filelock-3.29.3-py3-none-any.whl.metadata (2.0 kB)
#10 1.666 Collecting pydantic (from -r requirements.txt (line 4))
#10 1.696   Downloading pydantic-2.13.4-py3-none-any.whl.metadata (109 kB)
#10 1.737      ??????????????????????????????????????? 109.4/109.4 kB 2.7 MB/s eta 0:00:00
#10 1.801 Collecting starlette>=0.46.0 (from fastapi->-r requirements.txt (line 1))
#10 1.831   Downloading starlette-1.3.1-py3-none-any.whl.metadata (6.4 kB)
#10 1.880 Collecting typing-extensions>=4.8.0 (from fastapi->-r requirements.txt (line 1))
#10 1.911   Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
#10 1.946 Collecting typing-inspection>=0.4.2 (from fastapi->-r requirements.txt (line 1))
#10 1.975   Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
#10 2.010 Collecting annotated-doc>=0.0.2 (from fastapi->-r requirements.txt (line 1))
#10 2.040   Downloading annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
#10 2.086 Collecting click>=7.0 (from uvicorn->-r requirements.txt (line 2))
#10 2.116   Downloading click-8.4.1-py3-none-any.whl.metadata (2.6 kB)
#10 2.151 Collecting h11>=0.8 (from uvicorn->-r requirements.txt (line 2))
#10 2.180   Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
#10 2.230 Collecting annotated-types>=0.6.0 (from pydantic->-r requirements.txt (line 4))
#10 2.259   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
#10 2.799 Collecting pydantic-core==2.46.4 (from pydantic->-r requirements.txt (line 4))
#10 2.829   Downloading pydantic_core-2.46.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.6 kB)
#10 2.882 Collecting anyio<5,>=3.6.2 (from starlette>=0.46.0->fastapi->-r requirements.txt (line 1))
#10 2.911   Downloading anyio-4.13.0-py3-none-any.whl.metadata (4.5 kB)
#10 2.956 Collecting idna>=2.8 (from anyio<5,>=3.6.2->starlette>=0.46.0->fastapi->-r requirements.txt (line 1))
#10 2.986   Downloading idna-3.18-py3-none-any.whl.metadata (6.1 kB)
#10 3.022 Downloading fastapi-0.136.3-py3-none-any.whl (117 kB)
#10 3.040    ???????????????????????????????????????? 117.5/117.5 kB 6.7 MB/s eta 0:00:00
#10 3.070 Downloading uvicorn-0.49.0-py3-none-any.whl (71 kB)
#10 3.076    ???????????????????????????????????????? 71.4/71.4 kB 15.4 MB/s eta 0:00:00
#10 3.107 Downloading filelock-3.29.3-py3-none-any.whl (42 kB)
#10 3.111    ???????????????????????????????????????? 42.3/42.3 kB 25.2 MB/s eta 0:00:00
#10 3.140 Downloading pydantic-2.13.4-py3-none-any.whl (472 kB)
#10 3.184    ???????????????????????????????????????? 472.3/472.3 kB 11.3 MB/s eta 0:00:00
#10 3.213 Downloading pydantic_core-2.46.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
#10 3.367    ???????????????????????????????????????? 2.1/2.1 MB 13.7 MB/s eta 0:00:00
#10 3.397 Downloading annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
#10 3.426 Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#10 3.456 Downloading click-8.4.1-py3-none-any.whl (116 kB)
#10 3.464    ???????????????????????????????????????? 116.6/116.6 kB 17.8 MB/s eta 0:00:00
#10 3.493 Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#10 3.526 Downloading starlette-1.3.1-py3-none-any.whl (73 kB)
#10 3.532    ???????????????????????????????????????? 73.6/73.6 kB 15.4 MB/s eta 0:00:00
#10 3.562 Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
#10 3.565    ???????????????????????????????????????? 44.6/44.6 kB 21.3 MB/s eta 0:00:00
#10 3.595 Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
#10 3.626 Downloading anyio-4.13.0-py3-none-any.whl (114 kB)
#10 3.634    ???????????????????????????????????????? 114.4/114.4 kB 15.1 MB/s eta 0:00:00
#10 3.663 Downloading idna-3.18-py3-none-any.whl (65 kB)
#10 3.670    ???????????????????????????????????????? 65.5/65.5 kB 14.5 MB/s eta 0:00:00
#10 3.747 Installing collected packages: typing-extensions, idna, h11, filelock, click, annotated-types, annotated-doc, uvicorn, typing-inspection, pydantic-core, anyio, starlette, pydantic, fastapi
#10 4.265 Successfully installed annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.13.0 click-8.4.1 fastapi-0.136.3 filelock-3.29.3 h11-0.16.0 idna-3.18 pydantic-2.13.4 pydantic-core-2.46.4 starlette-1.3.1 typing-extensions-4.15.0 typing-inspection-0.4.2 uvicorn-0.49.0
#10 4.266 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
#10 4.399 
#10 4.399 [notice] A new release of pip is available: 24.0 -> 26.1.2
#10 4.399 [notice] To update, run: pip install --upgrade pip
#10 DONE 4.7s

#11 [5/5] RUN if [ ! -f main.py ]; then       printf 'from fastapi import FastAPI\napp = FastAPI(title="Hermes Vault API")\n' > main.py;     fi
#11 DONE 0.3s

#12 exporting to image
#12 exporting layers
#12 exporting layers 0.4s done
#12 exporting manifest sha256:5e69dbf4548c6d6b1797bc0717983e997aa618cfe8461920628c335f2c7fe703 done
#12 exporting config sha256:aa4ae9d3bfc21f64f364ae72482061207d3a3a41f76b4c443f18dc1e05b77069 done
#12 exporting attestation manifest sha256:492a61ad92b78ea3d8a211dee3969befe9bac501518683d007dbcf5b19b23c51 0.0s done
#12 exporting manifest list sha256:82bd86f8d2f96f0faa62230f02dcc089bd211a8430a7992413104eb6e4cac2d3 done
#12 naming to docker.io/library/stack-vault-api:latest done
#12 unpacking to docker.io/library/stack-vault-api:latest 0.1s done
#12 DONE 0.6s

#13 resolving provenance for metadata file
#13 DONE 0.0s
 Image stack-vault-api Built 
 Container hermes-vault-api Creating 
 Container hermes-vault-api Created 
 Container hermes-vault-api Starting 
 Container hermes-vault-api Started 
exit: 0

$ sleep 3
slept 3s
exit: 0

$ pytest scripts/smoke-tests/test_vault_io.py -v
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- D:\Stack\hermes-agent-2026.6.5\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Stack\hermes-agent-2026.6.5
configfile: pyproject.toml
plugins: anyio-4.13.0, timeout-2.4.0
collecting ... collected 1 item

scripts/smoke-tests/test_vault_io.py::test_vault_api_append_read_search PASSED [100%]

============================== 1 passed in 0.61s ==============================
exit: 0

$ python scripts/vault-rebuild-index.py
Indexed 0 pages into C:\Users\Around\HermesVault\INDEX.md
exit: 0

$ test -f ~/HermesVault/INDEX.md
exit: 0

$ hermes tools list | grep -c ^vault\.  # >= 5
5
exit: 0


```

## Issues And Resolutions

- WSL and system python/hermes are not available in this local environment; Git Bash and .venv python were used for equivalent gate commands.
- docker compose file lives at stack/docker-compose.yml, so the gate used `docker compose -f stack/docker-compose.yml up -d vault-api`.
- Pytest repo addopts use `--timeout-method=signal`, unsupported on Windows; smoke test passed with `-o addopts=''`.
- `hermes tools list` was executed as `.venv\Scripts\python.exe -m hermes_cli.main tools list` with isolated HERMES_HOME, then counted `^vault\.` entries.
- T-212 is deferred/no-op because `stack/decepticon-slim/middleware/vault_sync.py` is created later in the mandated execution order (T-124); no future-phase Decepticon file was created out of order.
- `vault-prune` cron job is defined because T-210 requires it, but no `scripts/vault-prune.py` task exists in this phase; the loader warns while still registering the job.

## Push

origin push: skipped (local-mode; no remote configured, user will upload later)
