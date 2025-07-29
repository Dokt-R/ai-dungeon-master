# Infrastructure and Deployment

This project supports easy self-hosting using **Docker Compose**. The provided `docker-compose.yml` orchestrates both the backend API and the Discord bot, allowing you to run the entire stack with minimal setup.

# Post-MVP: Direct Docker Run (No Cloning Needed)
As the project matures, we will implement the second phase of our deployment strategy.

At that stage, we will set up a CI/CD pipeline (using GitHub Actions) that automatically builds the Docker images and pushes them to a public container registry (like Docker Hub or GitHub Container Registry).

Once that is in place, a non-developer user will not need to clone the repository. They will be able to run the entire project with a simple command like docker run or by using a docker-compose.yml file that pulls the pre-built images directly from the public registry.