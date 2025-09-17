from invoke import task
import time
import json
import os

root_dir = os.path.dirname(os.path.abspath(__file__))

@task
def redis_server(c):
    """Start a Redis server instance."""
    c.run("docker run -d --name trios-redis -p 6379:6379 -v ../redis/data:/data redis:7-alpine")
    time.sleep(1)  # Give some time for the server to start
    c.run("redis-cli -h localhost -p 6379 ping")
    c.run("docker ps")
    print("🌱 Redis server started.")

@task
def redis_stop(c):
    """Stop the Redis server instance."""
    c.run("docker stop trios-redis")
    c.run("docker rm trios-redis")
    print("🛑 Redis server stopped.")