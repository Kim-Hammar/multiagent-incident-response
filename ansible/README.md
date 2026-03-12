# Ansible Playbook — CCS Incident Response Planner

Ansible playbook that installs Docker on a target host, clones the repository, and starts the application via `docker compose up`.

## Prerequisites

- **Control machine:** Ansible 2.12+ installed
- **Target host:** Ubuntu/Debian with SSH access (for remote hosts) and sudo privileges
- **For localhost:** The control machine itself must be Ubuntu/Debian

## What the Playbook Does

1. Installs Docker dependencies (`ca-certificates`, `curl`, `gnupg`)
2. Adds the official Docker GPG key and apt repository
3. Installs Docker CE, CLI, containerd, and the Compose plugin
4. Starts and enables the Docker service
5. Installs git
6. Clones the repository to the target directory
7. Builds and starts the app with `docker compose up -d --build`

## Variables

Defined in `vars.yml`:

| Variable      | Default                                                                  | Description                |
|---------------|--------------------------------------------------------------------------|----------------------------|
| `repo_url`    | `https://github.com/anonymous/anonymous-repo.git`             | GitHub repository URL      |
| `repo_branch` | `main`                                                                   | Branch to clone            |
| `app_dir`     | `/opt/ccs26_incident_response`                                           | Clone destination on host  |

Override variables on the command line with `-e`:

```bash
ansible-playbook playbook.yml -i inventory.yml -e "repo_branch=dev app_dir=/srv/myapp"
```

## Usage

### Dry Run (Check Mode)

```bash
cd ansible
ansible-playbook playbook.yml -i inventory.yml --check --limit local
```

### Deploy to Localhost

```bash
cd ansible
ansible-playbook playbook.yml -i inventory.yml --limit local
```

### Deploy to Remote Hosts

1. Edit `inventory.yml` and add hosts under the `servers` group:

   ```yaml
   servers:
     hosts:
       web1.example.com:
         ansible_user: ubuntu
   ```

2. Run the playbook:

   ```bash
   cd ansible
   ansible-playbook playbook.yml -i inventory.yml --limit servers
   ```

### Deploy to All Hosts

```bash
cd ansible
ansible-playbook playbook.yml -i inventory.yml
```

## Verification

After the playbook completes, visit `http://<host>:8888` to confirm the app is running.
