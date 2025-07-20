// Jenkinsfile (Scripted Pipeline)

def DOCKERHUB_USERNAME = 'dineshpardhu1'        // 🔁 change this
def IMAGE_NAME = 'affiliate-poster'
def DEPLOY_ENV = 'dev'                                    // can be parameterized
def GIT_BRANCH = "${env.BRANCH_NAME ?: 'main'}"
def BUILD_TAG = "${DEPLOY_ENV}-${env.BUILD_NUMBER}"
def DOCKER_IMAGE_TAG = "${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${BUILD_TAG}"
def KUBE_DEPLOY_FILE = "k8s/deployment-${DEPLOY_ENV}.yaml"

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
            sh "docker build -t ${DOCKER_IMAGE_TAG} ."
        }

        stage('Push to Docker Hub') {
            echo "Pushing Docker image to Docker Hub..."
            withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                sh """
                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                    docker push ${DOCKER_IMAGE_TAG}
                    docker logout
                """
            }
        }

        stage('Deploy to Kubernetes') {
            echo "Deploying to Kubernetes using ${KUBE_DEPLOY_FILE}..."

            // Replace the image in the deployment YAML and apply it
            sh """
                sed 's|IMAGE_PLACEHOLDER|${DOCKER_IMAGE_TAG}|' ${KUBE_DEPLOY_FILE} > deploy.yaml
                kubectl apply -f deploy.yaml
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


