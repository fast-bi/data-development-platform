# 🤝 Contributing to Fast.BI

Thank you for your interest in contributing to Fast.BI! This document provides guidelines and information for contributors who want to help improve the platform.

## 🎯 How to Contribute

There are many ways to contribute to Fast.BI:

- 🐛 **Report bugs** and issues
- 💡 **Suggest new features** and improvements
- 📖 **Improve documentation** and guides
- 🔧 **Submit code changes** and fixes
- 🧪 **Test and validate** deployments
- 🌍 **Translate** documentation to other languages
- 📢 **Share** Fast.BI with your network

## 🚀 Quick Start

### 1. **Fork the Repository**
```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/data-development-platform.git
cd data-development-platform

# Add the upstream remote
git remote add upstream https://github.com/fast-bi/data-development-platform.git
```

### 2. **Set Up Development Environment**
```bash
# Install required tools
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
# or for bug fixes
git checkout -b fix/your-bug-description
```

## 🔧 Development Setup

### **Prerequisites**
- Python 3.9+
- Docker and Docker Compose
- kubectl
- Terraform
- Terragrunt
- Helm

### **Local Development**
```bash
# Clone and setup
git clone https://github.com/fast-bi/data-development-platform.git
cd data-development-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
flake8
black --check .
isort --check-only .

# Format code
black .
isort .
```

### **Testing Fast.BI CLI**
```bash
# Test CLI help
python cli.py --help

# Test interactive mode (dry run)
python cli.py --dry-run

# Test with configuration file
python cli.py --config cli/deployment_configuration.yaml --dry-run
```

## 📝 Contribution Guidelines

### **Code Style**
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting

### **Commit Messages**
Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(cli): add AWS deployment support
fix(gcp): resolve billing account validation error
docs(deployment): update GCP prerequisites
test(cli): add unit tests for configuration validation
```

### **Pull Request Guidelines**
1. **Keep PRs focused** - One feature/fix per PR
2. **Write clear descriptions** - Explain what and why, not how
3. **Include tests** - Add tests for new functionality
4. **Update documentation** - Keep docs in sync with code changes
5. **Follow the template** - Use the provided PR template

## 🧪 Testing

### **Running Tests**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cli.py

# Run with coverage
pytest --cov=cli --cov-report=html

# Run integration tests
pytest tests/integration/ --integration
```

### **Test Structure**
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test data and fixtures
└── conftest.py     # Pytest configuration
```

### **Writing Tests**
- Write tests for new functionality
- Use descriptive test names
- Mock external dependencies
- Test both success and failure cases
- Aim for high test coverage

## 📚 Documentation

### **Documentation Structure**
```
docs/
├── deployment/     # Deployment guides
├── user-guide/     # User documentation
├── api/           # API reference
├── architecture/  # System architecture
└── contributing/  # Contributor guides
```

### **Writing Documentation**
- Use clear, concise language
- Include code examples
- Add screenshots for UI changes
- Keep documentation up-to-date with code
- Follow the established style guide

### **Documentation Tools**
- Markdown for all documentation
- Mermaid for diagrams
- Code blocks with syntax highlighting
- Links to related documentation

## 🐛 Bug Reports

### **Before Reporting**
1. Check existing issues for duplicates
2. Search documentation for solutions
3. Test with the latest version
4. Try to reproduce the issue

### **Bug Report Template**
```markdown
## Bug Description
Brief description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 13.0]
- Python: [e.g., 3.9.7]
- Fast.BI Version: [e.g., 1.0.0]
- Deployment Type: [e.g., GCP, On-Premise]

## Additional Information
Logs, screenshots, or other relevant details
```

## 💡 Feature Requests

### **Feature Request Template**
```markdown
## Feature Description
Brief description of the requested feature

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
What other approaches were considered?

## Additional Context
Any other relevant information
```

## 🔄 Pull Request Process

### **1. Create Your PR**
- Use the provided PR template
- Link related issues
- Add appropriate labels
- Request reviews from maintainers

### **2. Code Review**
- Address review comments promptly
- Make requested changes
- Add tests if needed
- Update documentation

### **3. Merge Requirements**
- All tests must pass
- Code review approved
- Documentation updated
- No merge conflicts

### **4. After Merge**
- Delete your feature branch
- Update your fork
- Celebrate your contribution! 🎉

## 🏗️ Architecture Contributions

### **Adding New Cloud Providers**
1. **Research Requirements**
   - Study existing cloud provider implementation
   - Understand provider-specific services
   - Identify authentication methods

2. **Create Provider Module**
   - Add provider to CLI configuration
   - Create Terraform modules
   - Implement provider-specific logic

3. **Add Tests and Documentation**
   - Unit tests for new functionality
   - Integration tests with provider
   - Complete deployment guide

### **Adding New Data Services**
1. **Service Integration**
   - Research service APIs and requirements
   - Create service configuration
   - Implement deployment logic

2. **Documentation and Testing**
   - Service-specific documentation
   - Configuration examples
   - Integration tests

## 🌍 Internationalization

### **Adding New Languages**
1. **Create Language Files**
   - Add translations to `locales/` directory
   - Update language configuration
   - Test with different locales

2. **Documentation Translation**
   - Translate user-facing documentation
   - Maintain translation quality
   - Keep translations up-to-date

## 📊 Performance Contributions

### **Performance Improvements**
- Profile code for bottlenecks
- Optimize database queries
- Improve resource usage
- Add performance monitoring

### **Scalability Enhancements**
- Horizontal scaling improvements
- Resource optimization
- Load balancing enhancements
- Caching strategies

## 🔒 Security Contributions

### **Security Improvements**
- Vulnerability assessments
- Security best practices
- Authentication enhancements
- Access control improvements

### **Reporting Security Issues**
- **DO NOT** create public issues for security problems
- Email security issues to: security@fast.bi
- Include detailed vulnerability information
- Allow time for security team response

## 🎉 Recognition

### **Contributor Recognition**
- Contributors are listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Significant contributions are highlighted in release notes
- Contributors may be invited to join the maintainer team

### **Contributor Levels**
- **Contributor**: First successful contribution
- **Regular Contributor**: Multiple contributions over time
- **Maintainer**: Consistent contributions and community involvement
- **Core Maintainer**: Project leadership and major decisions

## 📞 Getting Help

### **Community Resources**
- **GitHub Discussions**: Ask questions and get help
- **Discord**: Join our community chat
- **Documentation**: Comprehensive guides and tutorials
- **Issues**: Report bugs and request features

### **Maintainer Contact**
- **General Questions**: Create GitHub discussions
- **Security Issues**: support@fast.bi
- **Enterprise Support**: support@fast.bi
- **Project Leadership**: support@fast.bi

## 📋 Contributor Checklist

Before submitting your contribution, ensure you have:

- [ ] Read and understood this contributing guide
- [ ] Followed the code style guidelines
- [ ] Added appropriate tests
- [ ] Updated relevant documentation
- [ ] Used conventional commit messages
- [ ] Created a focused pull request
- [ ] Linked related issues
- [ ] Requested appropriate reviews

## 🎯 Next Steps

1. **Choose an issue** from the [good first issues](https://github.com/fast-bi/data-development-platform/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) label
2. **Set up your development environment** following the guide above
3. **Create a feature branch** and start coding
4. **Submit your pull request** and join the community!

---

**Thank you for contributing to Fast.BI!** 🚀

Your contributions help make Fast.BI better for everyone in the data community. Whether you're fixing a bug, adding a feature, or improving documentation, every contribution matters.

**Questions?** Don't hesitate to ask in [GitHub Discussions](https://github.com/fast-bi/data-development-platform/discussions) or reach out to the maintainer team.

**Happy coding!** 💻✨
