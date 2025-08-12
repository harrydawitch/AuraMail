# AuraMail

An intelligent email automation system that monitors your Gmail inbox, classifies emails using AI, and helps you manage responses efficiently with a modern desktop GUI.

## 🌟 Features

### Core Functionality
- **Intelligent Email Classification**: Automatically categorizes incoming emails as "notify" (important) or "ignore" (spam/promotional)
- **Smart Summarization**: AI-powered email summaries for quick understanding
- **Draft Response Generation**: Automatically generates contextual email responses
- **Human-in-the-Loop**: Review and approve responses before sending
- **Real-time Monitoring**: Continuously monitors your Gmail inbox
- **Persistent State**: Maintains email processing state across sessions

### User Interface
- **Modern Desktop GUI**: Built with CustomTkinter for a sleek interface
- **Email Categories**: Organized views (Home, Notify, Ignore, Human Review)
- **Draft Management**: Review, edit, and approve AI-generated responses
- **System Tray Integration**: Minimizes to system tray for background operation

### Technical Features
- **LangGraph Workflows**: Sophisticated AI workflow orchestration
- **Gmail API Integration**: Full Gmail read/send permissions
- **SQLite Persistence**: Workflow checkpointing and state management
- **Multi-threaded Architecture**: Separate backend and frontend threads
- **Error Handling**: Robust error handling and recovery

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Gmail account with API access
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/harrydawitch/AuraMail.git
   cd AuraMail 
   python -m venv .venv
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Gmail API credentials**
   ```bash
   python setup.py
   ```
   ### **Note**: Go to -> [**setup.md**](./setup.md) (RECOMMEND)
   
   This will:
   - Guide you through Gmail API setup
   - Help you download `credentials.json`
   - Run OAuth flow to generate `token.json`
   - Configure OpenAI API key and your email


4. **Run the application**
   
   Double click to [AuraMail.vbs](./AuraMail.vbs) to start the system



## 📁 Project Structure

```
AuraMail/
├── 🚀 main.py                 # Application entry point
├── ⚙️ setup.py               # Gmail API and environment setup
├── 📋 requirements.txt       # Python dependencies
├── 📂 src/
│   ├── 🔧 backend.py         # Core email processing logic
│   ├── 🔗 connect.py         # Frontend/backend communication
│   ├── 📊 email_service.py   # Email data management
│   ├── 🤖 nodes.py          # AI workflow components
│   ├── 💬 prompts.py        # AI prompts and templates
│   ├── 📝 states.py         # Workflow state management
│   ├── 🛠️ utils.py          # Utility functions
│   ├── 🏗️ workflow.py       # Workflow definitions
│   └── 📂 ui/
│       └── 🖥️ gui.py        # Desktop interface
└── 📂 db/                    # Data storage
    ├── checkpoints.sqlite    # Workflow persistence
    ├── email_state.json     # Processing state
    ├── emails.json          # Email data
    └── workflows.json       # Active workflows
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file or use the setup script:
```env
OPENAI_API_KEY=your_openai_api_key
MY_EMAIL=your_email@gmail.com
```

### Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop Application)
4. Download `credentials.json`
5. Run `python setup.py` to complete setup

### Application Settings
Modify in `main.py`:
```python
app = EmailApp(
    workflow_model="gpt-4o-mini",  # AI model to use
    check_interval=40,             # Email check interval (seconds)
)
```

## 🤖 How It Works

### Email Processing Workflow

1. **Email Monitoring**: Continuously polls Gmail for new emails
2. **Classification**: AI categorizes emails as "notify" or "ignore"
3. **Summarization**: Generates concise summaries for important emails
4. **Response Generation**: Creates draft responses based on context
5. **Human Review**: User approves, edits, or rejects responses
6. **Sending**: Approved responses are sent via Gmail API

### AI Workflow Architecture

The system uses LangGraph for sophisticated AI workflows:

- **EmailResponseWorkflow**: Processes incoming emails
- **SendEmailWorkflow**: Handles outgoing email composition
- **Checkpointing**: Persists workflow state for resume capability

## 🎯 Usage

### Main Interface Categories

- **Home**: All incoming emails
- **Notify**: Important emails requiring attention
- **Ignore**: Filtered out emails (spam, newsletters)
- **Pending**: Emails with draft responses awaiting approval
- **Send Email**: Send email to the person you want with the help of AI

### Email Response Flow

1. Receive email → Auto-classification
2. Important email → Generate summary
3. User decides to respond → Generate draft
4. Review draft → Approve/Reject
5. Send response → Email delivered

### Compose New Emails

1. Enter recipient and intent 
2. Click "Generate Draft" button
3. AI generates draft
4. Review and send

## ⚙️ Technical Details

### Key Components

- **EmailManager**: Orchestrates the entire email processing pipeline
- **WorkflowProcessor**: Manages AI workflow execution
- **EmailState**: Tracks processed emails and prevents duplicates
- **Communicator**: Handles frontend-backend communication

### AI Models Used

- **Classification**: Determines email importance
- **Summarization**: Creates concise email summaries  
- **Response Generation**: Writes contextual replies

### Data Persistence

- **SQLite**: Workflow checkpoints and thread management
- **JSON**: Email data, application state, and configuration

## 🛠️ Customization

### Modify AI Behavior

Edit prompts in `src/prompts.py`:
- `classifier_system_prompt`: Email classification rules
- `summary_system_prompt`: Summarization instructions
- `writer_system_prompt`: Response generation guidelines

### Adjust Classification Rules

Modify `default_rules` in `src/prompts.py` to change how emails are categorized.

### Change UI Appearance

The GUI uses CustomTkinter - modify `src/ui/gui.py` for interface changes.

## 🔒 Security & Privacy

- **Local Processing**: All email processing happens locally
- **Secure Storage**: Credentials stored securely in user directories
- **No Data Sharing**: No email data sent to external services (except OpenAI for AI processing)
- **OAuth 2.0**: Secure Gmail authentication

## 🐛 Troubleshooting

### Common Issues

1. **Gmail API Errors**: Ensure credentials.json is valid and OAuth completed
2. **OpenAI API Errors**: Verify API key and sufficient credits
3. **Database Lock Errors**: Close other instances of the application
4. **UI Not Responding**: Check backend thread status in console


## 🤝 Contributing
Any contribution are welcome
1. Fork the repository
2. Create a feature branch 
3. Commit your changes 
4. Push to the branch 
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangGraph**: For workflow orchestration
- **LangChain**: For AI model integration
- **CustomTkinter**: For modern GUI components
- **Gmail API**: For email access and sending

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing GitHub issues
3. Create a new issue with detailed description
4. Any further question please send it to my email: tl376284@gmail.com

---

**Note**: This application requires Gmail API access and OpenAI API key. Ensure you comply with both services' terms of use and rate limits.
=======
# **AuraMail**
>>>>>>> 815021639ecec10d69d47809869bef2a5e2b4116
