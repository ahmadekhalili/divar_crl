looger should import from methods


uvicorn main:app --host 127.0.0.1 --port 8001 --log-level debug --access-log --reload     # run project

in fastapi, everything start from methods/listen_redis. listen to redis and if found records, write it to mongodb.




# notes:
- if you removed data stream (And maybe group) of redis you will saw endless log writings. should restart fastapi to fix




