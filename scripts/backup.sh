#!/bin/bash
BACKUP_DIR=/opt/bots/protocols-bot/backups
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /opt/bots/protocols-bot/storage/protocols.db $BACKUP_DIR/protocols_backup_${DATE}.db
tar -czf $BACKUP_DIR/protocols_backup_${DATE}_files.tar.gz -C /opt/bots/protocols-bot/storage protocols
find $BACKUP_DIR -name '*.db' -mtime +30 -delete
find $BACKUP_DIR -name '*.tar.gz' -mtime +30 -delete
echo "Backup completed: $DATE"
