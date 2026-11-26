# Service template

Use this template to write a new service for your Digital Twins and propose it to the admin.

## Files

| File | What it is |
|---|---|
| `my_service.py` | the service: the `SERVICE` description and the `run()` function. **This is the file you upload.** |
| `prova_locale.py` | tries `my_service.py` on your PC with fake data |
| `service_check.py` | the same automatic checks the platform runs on upload (used by `prova_locale.py`) |

## Steps

1. Edit `my_service.py`: give the service a name, describe its parameters in `SERVICE["params"]`
   and write what it computes in `run()`. The example computes the rate of change of a parameter.
2. Try it:
   ```
   pip install pymongo numpy mongomock
   python prova_locale.py
   ```
   It prints the result of three cycles, or the errors the platform would report.
3. In the dashboard open **Request service**, upload `my_service.py`, add a note for the admin
   (what the service does, what it is for) and send the request.
4. The admin reads the code and approves or rejects it. You see the outcome, and the admin's
   reason if there is one, in the same page. Once approved, the service is in the catalog of
   **Create DT** for every user, next to the built-in services.

## Which DR parameters the service uses

By default a service works on any numeric parameter: the user chooses the inputs in Create DT.
If yours needs specific parameters, list them in `SERVICE["parameters"]` with the names of the
platform's parameter list (the same names used when registering a Digital Replica):

```python
"parameters": {"Temperature": {}, "Humidity": {}},
```

In Create DT the user can then choose only inputs with those parameters.
If a parameter is not in the list yet, give its type (`float` or `int`) and unit:

```python
"parameters": {"Temperature": {}, "Solar radiation": {"type": "float", "unit": "W/m²"}},
```

It travels with your request: the admin sees it next to the code and, approving the service,
adds it to the parameter list, so you can then register Digital Replicas that send it.

## What `run()` receives

- `db`: the database of the DT. The measures of a Digital Replica are in `db[inp["collection"]]`,
  one document per measure: `{"dr_id": ..., "<parameter>": value, "orario_invio": datetime}`.
- `inp`: the input chosen in Create DT, `{"dr_id", "parameter", "collection"}`.
  `run()` is called once per input at every cycle. With `"min_inputs": 0` and no inputs it is
  called once per cycle with `inp = None` (e.g. a service that checks an external site).
- `params`: the values of the parameters, with the defaults already applied.
- `instance_id`: the id of this copy of the service in the DT. Use it in the key of anything
  you save in `db` (see `threshold_check` in the built-in services), so two copies do not mix.

Return a `dict` (numbers, text, lists, dicts) or `None` when there is nothing to save.
The platform saves it in `service_output` and shows it in the **Service** page.

## Rules

- Imports allowed: `math`, `statistics`, `datetime`, `time`, `json`, `re`, `random`,
  `collections`, `itertools`, `functools`, `numpy`, `urllib.request`, `urllib.error`, `urllib.parse`.
  Need another library? Write it in the note of the request.
- Not allowed: `os`, `sys`, `subprocess`, `socket`, `open`, `eval`, `exec`, `__import__`,
  `getattr`, attributes starting with `__`.
- No loops that never end, threads or web servers: the platform runs `run()` in a loop for you.
- `SERVICE` must contain only fixed values; the file must be at most 100 KB.
- The service only sees the database of the DT it is added to.
