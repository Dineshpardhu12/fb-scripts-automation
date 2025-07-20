// Jenkinsfile (Scripted Pipeline)

def DOCKERHUB_USERNAME = 'dineshpardhu1'
def IMAGE_NAME = 'affiliate-poster'
def DEPLOY_ENV = 'dev'
def GIT_BRANCH = "${env.BRANCH_NAME ?: 'main'}"
def BUILD_TAG = "${DEPLOY_ENV}-${env.BUILD_NUMBER}"
def DOCKER_IMAGE_TAG = "${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${BUILD_TAG}"
def KUBE_DEPLOY_FILE = "k8s/deployment-${DEPLOY_ENV}.yaml"
def DOCKER_PATH = "/usr/local/bin"  // ✅ Your docker path

node {
    try {
        stage('Clean Workspace') {
            echo "Cleaning workspace..."
            cleanWs()
        }

        stage('Checkout Code') {
            echo "Checking out code..."
            checkout scm
        }

        stage('Build Docker Image') {
            echo "Building Docker image: ${DOCKER_IMAGE_TAG}"
            sh """
                export PATH="${DOCKER_PATH}:\$PATH"
                docker build -t ${DOCKER_IMAGE_TAG} .
            """
        }

        stage('Push to Docker Hub') {
            echo "Pushing Docker image to Docker Hub..."
            withCredentials([usernamePassword(credentialsId: '11728cc9-b713-4bf8-925b-b1e1c03a12f8', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
            sh """
                export PATH="${DOCKER_PATH}:\$PATH"
                echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                docker push ${DOCKER_IMAGE_TAG}
                docker logout
            """
            }
        }

        stage('Deploy to Kubernetes') {
            echo "Deploying to Kubernetes using ${KUBE_DEPLOY_FILE}..."
            sh """
                export PATH="${DOCKER_PATH}:\$PATH"
                sed 's|IMAGE_PLACEHOLDER|${DOCKER_IMAGE_TAG}|' ${KUBE_DEPLOY_FILE} > deployment-dev.yaml
                kubectl apply -f deployment-dev.yaml
            """
        }

        stage('Post Deploy Cleanup') {
            echo "Cleaning up workspace after build"
            cleanWs()
        }
    } catch (e) {
        currentBuild.result = 'FAILURE'
        echo "Pipeline failed: ${e.message}"
        throw e
    }
}
