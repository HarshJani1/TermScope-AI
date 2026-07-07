pipeline {
    agent {
        docker {
            image 'username/termscope-ci-common:latest'
            reuseNode true
        }
    }

    environment {
        FLASK_ENV = 'testing'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // --- BACKEND DEPENDENCIES STAGE REMOVED ---

        stage('Backend Tests') {
            steps {
                dir('backend') {
                    // No virtual environment or pip install needed anymore!
                    sh 'pytest'
                }
            }
        }

        // --- FRONTEND DEPENDENCIES STAGE REMOVED ---

        stage('Frontend Lint') {
            steps {
                dir('frontend') {
                    sh 'npm run lint'
                }
            }
        }

        stage('Frontend Build') {
            steps {
                dir('frontend') {
                    sh 'npm run build'
                }
            }
        }
    }
}
