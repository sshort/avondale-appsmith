#!/usr/bin/env bash
set -euo pipefail

PROXMOX_HOST="root@192.168.1.2"
SSH_KEY="$HOME/.ssh/id_root_lan"
TEMPLATE="ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
TEMPLATE_PATH="local:vztmpl/${TEMPLATE}"
HOSTNAME="appsmith"
CORES=2
MEMORY=4096
DISK_SIZE=32
STORAGE="local-lvm"
BRIDGE="vmbr0"

echo "=== Appsmith LXC Deployment ==="
echo ""

# --- Step 1: Validate SSH connectivity ---
echo "[1/10] Testing SSH connectivity to Proxmox..."
ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$PROXMOX_HOST" "echo OK" >/dev/null 2>&1 || {
  echo "ERROR: Cannot SSH to $PROXMOX_HOST. Ensure SSH key auth is configured."
  exit 1
}
echo "  SSH OK"

# --- Step 2: Download Ubuntu template if needed ---
echo "[2/10] Checking for Ubuntu 24.04 LXC template..."
if ! ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pveam list local | grep -q '$TEMPLATE'" 2>/dev/null; then
  echo "  Template not found. Downloading..."
  ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pveam download local $TEMPLATE"
  echo "  Template downloaded."
else
  echo "  Template already present."
fi

# --- Step 3: Get next available VMID ---
echo "[3/10] Getting next available VMID..."
VMID=$(ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pvesh get /cluster/nextid")
echo "  VMID: $VMID"

# --- Step 4: Create LXC ---
echo "[4/10] Creating LXC container..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct create $VMID $TEMPLATE_PATH \
  --hostname $HOSTNAME \
  --cores $CORES \
  --memory $MEMORY \
  --rootfs $STORAGE:$DISK_SIZE \
  --net0 name=eth0,bridge=$BRIDGE,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1"
echo "  LXC created."

# --- Step 5: Start LXC ---
echo "[5/10] Starting LXC container..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct start $VMID"

echo "  Waiting for container to start..."
for i in $(seq 1 30); do
  STATUS=$(ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct status $VMID" 2>/dev/null || echo "unknown")
  if echo "$STATUS" | grep -q "status: running"; then
    echo "  Container is running."
    break
  fi
  sleep 2
done

echo "  Waiting for network to initialize..."
sleep 10

# --- Step 6: Get LXC IP ---
echo "[6/10] Getting LXC IP address..."
LXC_IP=$(ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- ip -4 addr show eth0 | grep -oP 'inet \K[\d.]+'" 2>/dev/null || echo "")
if [ -z "$LXC_IP" ]; then
  echo "  WARNING: Could not determine IP. Check manually with: pct exec $VMID -- ip addr show eth0"
else
  echo "  IP: $LXC_IP"
fi

# --- Step 7: Install Docker inside LXC ---
echo "[7/10] Installing Docker inside LXC..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- apt-get update -qq"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- apt-get install -y -qq ca-certificates curl gnupg"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- install -m 0755 -d /etc/apt/keyrings"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- chmod a+r /etc/apt/keyrings/docker.asc"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- bash -c 'echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" > /etc/apt/sources.list.d/docker.list'"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- apt-get update -qq"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
echo "  Docker installed."

# --- Step 8: Create docker-compose.yml inside LXC ---
echo "[8/10] Creating Appsmith docker-compose.yml..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- mkdir -p /opt/appsmith"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- bash -c 'cat > /opt/appsmith/docker-compose.yml << '\''EOF'\''
services:
  appsmith:
    image: index.docker.io/appsmith/appsmith-ee:latest
    container_name: appsmith
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./stacks:/appsmith-stacks
    restart: unless-stopped
EOF'"

# --- Step 9: Create systemd service for auto-start ---
echo "[9/10] Creating systemd service for Appsmith..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- bash -c 'cat > /etc/systemd/system/appsmith.service << '\''EOF'\''
[Unit]
Description=Appsmith Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/appsmith
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF'"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- systemctl daemon-reload"
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- systemctl enable appsmith"
echo "  Systemd service enabled."

# --- Step 10: Start Appsmith ---
echo "[10/10] Starting Appsmith..."
ssh -i "$SSH_KEY" "$PROXMOX_HOST" "pct exec $VMID -- docker compose -f /opt/appsmith/docker-compose.yml up -d"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "  LXC ID:     $VMID"
echo "  Hostname:   $HOSTNAME"
if [ -n "$LXC_IP" ]; then
  echo "  IP Address: $LXC_IP"
  echo "  URL:        http://$LXC_IP"
fi
echo ""
echo "  Appsmith is starting up. This can take up to 5 minutes."
echo "  Once ready, open http://$LXC_IP in your browser and create an admin account."
echo ""
echo "  Useful commands:"
echo "    ssh $PROXMOX_HOST pct status $VMID"
echo "    ssh $PROXMOX_HOST pct exec $VMID -- docker compose -f /opt/appsmith/docker-compose.yml logs -f"
echo "    ssh $PROXMOX_HOST pct enter $VMID"
