# Ansible Runner Switch

This is a custom Home Assistant component that allows you to run Ansible playbooks and monitor their progress using Home Assistant switches.

## Installation

1. Copy the ansible_playbook folder into your Home Assistant custom_components directory.
2. Install the ansible package on your Home Assistant system by running pip install ansible.

## Configuration

To use the Ansible Playbook Switch, you'll need to add a new platform to your Home Assistant switch configuration. Here's an example configuration that runs a single playbook:

```yaml

button:
  - platform: ansible_playbook
    playbooks:
      - directory: dummy
        playbook_file: main.yml
        fault_password_file: vault.txt
        button_name: My Dummy Playbook
        button_id: dummy

```

You can specify multiple playbooks by adding additional items to the playbooks list. Each playbook must have a unique switch_name.
Usage

Once you've added the Ansible Playbook Switch to your Home Assistant configuration, you can use the switches to run your playbooks.

When you turn on the switch, the playbook will start running. The switch will remain on until the playbook has completed, at which point it will turn off. If the playbook encounters an error or fails to complete, the switch will turn off and an error message will be displayed in the Home Assistant logs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

* This project was inspired by the Home Assistant demo switch platform.
* The Ansible Playbook Switch uses the Ansible Python API to execute playbooks.
