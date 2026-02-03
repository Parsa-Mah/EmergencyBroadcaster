# Baleh Office Automation Bot

A Telegram-compatible bot for Baleh messenger that handles company issue tracking and broadcasting.

## Features

### ✅ Issue Broadcasting System
- Admins can broadcast company issues to all users
- Each issue gets a unique ID (ISSUE-001, ISSUE-002, etc.)
- Issues are tracked in PostgreSQL database

### ✅ Admin Dashboard with Inline Keyboards
- View all open issues with interactive buttons
- Click on any issue to view full details
- Close issues with resolution descriptions
- Resolution automatically broadcast to all users

### ✅ User Management
- Automatic user registration on /start
- Role-based access control (admin/employee)
- Track user activity (last_seen)
- Support for organizational hierarchy

### ✅ Security
- Only admins can broadcast issues
- Only admins can view and close issues
- Environment-based admin configuration

## Installation

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database
- Baleh bot token (create bot via @BotFather on Baleh)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
BOT_TOKEN=your_bale_bot_token_here
ADMIN_ID=your_numeric_user_id_here
DATABASE_URL=postgresql://username:password@localhost:5432/baleh_bot
```

**To get your ADMIN_ID:**
1. Run the bot once
2. Send `/start` to your bot
3. Check the console output for your user ID
4. Add that number to `.env`

### 4. Initialize Database

```bash
python models.py
```

This creates the necessary tables:
- `users` - User information and roles
- `issues` - Issue tracking

### 5. Run the Bot

```bash
python bot.py
```

## Usage

### For Regular Users

**Commands:**
- `/start` - Register with the bot
- `/help` - Show available commands

**What Users Receive:**
- Broadcast notifications when new issues are reported
- Resolution notifications when issues are closed

### For Admins

**Commands:**
- `/start` - Register/login
- `/help` - Show all commands (including admin commands)
- `/broadcast <message>` - Broadcast a new issue to all users
- `/issues` - View all open issues (with interactive buttons)
- `/myissues` - View only issues you created

**Admin Workflow:**

1. **Broadcasting an Issue:**
   ```
   /broadcast Server maintenance scheduled for tonight at 10 PM
   ```
   - Issue gets unique ID (e.g., ISSUE-001)
   - Sent to all registered users
   - Stored in database as "open"

2. **Viewing Open Issues:**
   ```
   /issues
   ```
   - Shows list of all open issues with buttons
   - Click any issue to view full details

3. **Closing an Issue:**
   - Click on an issue from /issues
   - Click "✅ Close This Issue" button
   - Bot asks for resolution description
   - Type the resolution and send
   - Resolution is broadcast to all users
   - Issue marked as closed in database

## Database Schema

### Users Table
```sql
- user_id (BigInteger, Primary Key) - Baleh user ID
- username (String) - Baleh username
- first_name (String) - User's first name
- role (String) - 'admin' or 'employee'
- status (String) - 'pending_approval' or 'active'
- employee_id (String) - Internal company ID
- full_name (String) - Full legal name
- department (String) - Department name
- job_title (String) - Job title
- phone_number (String) - Contact number
- manager_id (BigInteger) - Foreign key to users.user_id
- created_at (DateTime) - Registration timestamp
- last_seen (DateTime) - Last activity timestamp
```

### Issues Table
```sql
- id (Integer, Primary Key, Auto-increment) - Issue number
- message (Text) - Issue description
- created_by (BigInteger) - Foreign key to users.user_id
- status (String) - 'open' or 'closed'
- created_at (DateTime) - When issue was created
- resolution (Text) - How issue was resolved
- closed_by (BigInteger) - Foreign key to users.user_id
- closed_at (DateTime) - When issue was closed
```

## Making Users Admins

Currently, you need to manually update the database to make users admins:

```sql
-- Connect to your PostgreSQL database
psql -U username -d baleh_bot

-- Make a user an admin
UPDATE users SET role = 'admin' WHERE user_id = 123456789;

-- Verify
SELECT user_id, first_name, role FROM users;
```

**Future Enhancement:** Add a `/promote` command for super admins.

## Architecture Decisions

### Why Inline Keyboards?
- Better UX than text-based menus
- Faster interaction (one click vs typing commands)
- Visual feedback
- Professional appearance

### Why PostgreSQL?
- Reliable data persistence
- ACID compliance
- Support for complex queries
- Scalable for future features

### Sync vs Async
- Using synchronous SQLAlchemy for simplicity
- pyTelegramBotAPI handles threading internally
- Easy to understand and maintain
- Sufficient for most office automation needs

## Code Structure

```
.
├── models.py          # Database models (User, Issue)
├── bot.py             # Main bot logic and handlers
├── requirements.txt   # Python dependencies
├── .env              # Environment variables (not in git)
└── .env.example      # Template for .env
```

## Key Features Explained

### 1. Issue Tracking
Every broadcast message is stored as an "Issue" with:
- Unique sequential ID
- Creation timestamp
- Creator's user ID
- Current status (open/closed)

### 2. Interactive Admin Interface
Admins see issues as clickable buttons:
```
📋 Open Issues (3)

Click on an issue to view details and close it:
[ISSUE-001: Server maintenance scheduled...]
[ISSUE-002: Printer on 3rd floor not working...]
[ISSUE-003: Network issues in Building A...]
```

### 3. Issue Resolution Workflow
```
Admin clicks issue → Views full details → Clicks "Close" 
→ Provides resolution → Issue closed → Resolution broadcast
```

### 4. Automatic User Tracking
Every message updates the user's `last_seen` timestamp, useful for:
- Activity monitoring
- Inactive user cleanup
- Compliance reporting

## Future Enhancements

### Suggested Features
1. **Issue Categories** - Tag issues as IT, HR, Facilities, etc.
2. **Priority Levels** - High, Medium, Low
3. **Assigned Issues** - Assign issues to specific admins
4. **Issue Comments** - Thread discussions on issues
5. **Search Function** - Search through closed issues
6. **Statistics Dashboard** - Issue resolution metrics
7. **Scheduled Messages** - Schedule broadcasts
8. **File Attachments** - Attach photos/documents to issues
9. **User Permissions** - Department-based visibility
10. **Issue Templates** - Pre-defined issue types

### Database Migrations
For production, consider using Alembic:
```bash
pip install alembic
alembic init migrations
```

## Troubleshooting

### Bot doesn't respond
- Check BOT_TOKEN is correct
- Verify API_URL points to Baleh: `https://tapi.bale.ai/bot{0}/{1}`
- Check bot process is running

### Can't broadcast
- Verify ADMIN_ID is set correctly
- Check user role is 'admin' in database
- Ensure user has sent /start first

### Database errors
- Verify DATABASE_URL format
- Check PostgreSQL is running
- Run `python models.py` to create tables
- Check PostgreSQL logs

### Users not receiving messages
- Bot needs to be started by each user first
- Check for errors in console (failed sends)
- Verify users are in database: `SELECT * FROM users;`

## Security Considerations

### Production Checklist
- [ ] Use strong PostgreSQL password
- [ ] Never commit .env file to git
- [ ] Restrict database access to localhost
- [ ] Use environment variables for all secrets
- [ ] Add rate limiting for broadcast commands
- [ ] Implement input validation/sanitization
- [ ] Add logging for admin actions
- [ ] Regular database backups
- [ ] SSL/TLS for database connections

## Support

For issues specific to:
- **Baleh API**: Check Baleh documentation
- **pyTelegramBotAPI**: https://github.com/eternnoir/pyTelegramBotAPI
- **SQLAlchemy**: https://docs.sqlalchemy.org/

## License

[Add your license here]

## Contributing

[Add contribution guidelines]

---

**Version:** 1.0.0  
**Last Updated:** February 2026
