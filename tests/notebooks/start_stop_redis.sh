docker run -d --name my-redis -p 6379:6379 -v ./redis/data:/data redis:7-alpine
docker stop my-redis
docker rm my-redis
