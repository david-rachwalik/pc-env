# Use lightweight Node.js (v20) image
FROM node:20-alpine

# Set the working directory
WORKDIR /repos

# Install Angular (v18) globally
RUN npm install -g @angular/cli@18

# Map the /repos directory to the host to allow project files to be accessible
VOLUME [ "/repos" ]

# Default command to create a new Angular project with a passed argument
ENTRYPOINT ["ng", "new"]
# Allow the project name to be passed as an argument, with --defaults to avoid prompts
CMD ["project-name", "--defaults"]


# --- Usage Example (run from project root, build image, and run container) ---
# cd "${env:USERPROFILE}\Repos\pc-env"
# docker build -t angular-creator -f docker/angular_new/Dockerfile .
# docker run --rm -v "${env:USERPROFILE}\Repos:/repos" angular-creator <app-name>
