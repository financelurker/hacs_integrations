# const.py

DOMAIN = "ansible_playbook"
DEFAULT_NAME = "Ansible Playbook"
DEFAULT_ICON = "mdi:book-play"
DEFAULT_LIMIT = "all"
DEFAULT_TAGS = "all"
DEFAULT_OPTIONS = None

CONF_NAME = "name"
CONF_PLAYBOOK_PATH = "playbook_path"
CONF_HOSTS = "hosts"
CONF_SWITCH_NAME = "switch_name"
CONF_INVENTORY_PATH = "inventory_path"
CONF_LIMIT = "limit"
CONF_TAGS = "tags"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SUDO = "sudo"
CONF_SUDO_USER = "sudo_user"
CONF_EXTRA_VARS = "extra_vars"
CONF_OPTIONS = "options"
CONF_PLAYBOOKS = "playbooks"
CONF_VAULT_PASSWORD_FILE = "fault_password_file"

ATTR_HOSTS_COUNT = "hosts_count"
ATTR_STEPS_COUNT = "steps_count"
ATTR_PLAYBOOK = "playbook"
ATTR_TAGS = "tags"
ATTR_LIMIT = "limit"
ATTR_OPTIONS = "options"

SERVICE_PLAY = "play"
SERVICE_STOP = "stop"