# SmartEmailBot

An intelligent email automation system that monitors your Gmail inbox, classifies emails using AI, and helps you manage responses efficiently with a modern desktop GUI.

## 📥 Download

**Latest Release**: [Download SmartEmailBot Setup](https://github.com/harrydawitch/SmartEmailBot/releases/latest/download/SmartEmailBot_setup.exe)

Or visit the [Releases page](https://github.com/harrydawitch/SmartEmailBot/releases) for all versions.

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

### Installation
1. **Download**: Click the download link above to get `SmartEmailBot_setup.exe`
2. **Run Setup**: Execute the downloaded file and follow the installation wizard
3. **Launch**: Start SmartEmailBot from your desktop or start menu

### Prerequisites
- Windows 10/11 (64-bit)
- Internet connection for AI processing
- Gmail account
- OpenAI API key

### First-Time Setup
1. **Gmail API**: Set up Gmail API credentials (see detailed setup guide below)
2. **OpenAI API**: Configure your OpenAI API key
3. **Launch**: Start the application and complete initial configuration

## ⚙️ Configuration

### Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create credentials (OAuth 2.0 client ID)
5. Download `credentials.json` file
6. Place it in the application's config directory

### OpenAI API Setup
1. Sign up at [OpenAI](https://openai.com/)
2. Generate an API key
3. Enter the key in SmartEmailBot settings

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

## 🛠️ Technical Details

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

## 🔧 Customization

### Modify AI Behavior

Edit prompts in the application settings:
- Classification rules for email categorization
- Summarization instructions
- Response generation guidelines

### Adjust Classification Rules

Modify classification rules through the settings interface to change how emails are categorized.

## 🔒 Security & Privacy

- **Local Processing**: All email processing happens locally
- **Secure Storage**: Credentials stored securely in user directories
- **No Data Sharing**: No email data sent to external services (except OpenAI for AI processing)
- **OAuth 2.0**: Secure Gmail authentication

## 🐛 Troubleshooting

### Common Issues

1. **Installation Issues**: 
   - Run as administrator if installation fails
   - Ensure Windows Defender/antivirus allows the installation
   
2. **Gmail API Errors**: 
   - Ensure credentials.json is valid and OAuth completed
   - Check Gmail API quotas in Google Cloud Console
   
3. **OpenAI API Errors**: 
   - Verify API key and sufficient credits
   - Check API rate limits
   
4. **Application Not Starting**: 
   - Check Windows Event Viewer for error details
   - Ensure all dependencies are installed

### Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Look for error logs in the application directory
3. Contact support: tl376284@gmail.com

## 🤝 Contributing

Contributions are welcome! 
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
4. Email support: tl376284@gmail.com

---

**Note**: This application requires Gmail API access and OpenAI API key. Ensure you comply with both services' terms of use and rate limits.

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 100MB available space
- **Network**: Internet connection required for AI processing