# DevOps-Learning
 
To create an image:

```bash
docker build . -t doc_chat_api
```

To Run the api as a container:

```bash
docker run --rm -it --name doc_chat_instance  -p 80:80/tcp doc_chat_api:latest
```
