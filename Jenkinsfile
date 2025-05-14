pipeline {
    agent any

    environment {
        ANSIBLE_INVENTORY = 'inventory.ini'
        ANSIBLE_PLAYBOOK = 'playbook.yml'
    }

    stages {
        stage('Checkout') {
            steps {
        echo "Le code est déjà extrait par Jenkins."
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
