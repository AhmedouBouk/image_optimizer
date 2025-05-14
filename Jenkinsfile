pipeline {
    agent any

    environment {
        ANSIBLE_INVENTORY = 'inventory.ini'
        ANSIBLE_PLAYBOOK = 'playbook.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/TON-UTILISATEUR/TON-REPO.git'
            }
        }

        stage('Install Ansible') {
            steps {
                sh 'apt-get update && apt-get install -y ansible'
            }
        }

        stage('Run Ansible Playbook') {
            steps {
                sh 'ansible-playbook -i $ANSIBLE_INVENTORY $ANSIBLE_PLAYBOOK'
            }
        }
    }
}
