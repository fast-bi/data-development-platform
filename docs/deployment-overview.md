# Fast.BI Deployment Overview

This document provides an overview of all available deployment options for Fast.BI and guides you to the appropriate deployment guide for your needs.

## 🎯 Deployment Options

Fast.BI supports multiple deployment scenarios to meet different requirements:

### 1. **Google Cloud Platform (GCP)** - 🥇 **Recommended & Fully Tested**
- **Best for**: Production deployments, GCP users, full automation
- **Features**: Complete infrastructure automation, GKE cluster, managed services
- **Complexity**: Medium (guided CLI deployment)
- **Cost**: Pay-as-you-use GCP resources
- **Status**: ✅ **Fully tested and production-ready**

**📖 [GCP Deployment Guide](gcp-deployment.md)**

### 2. **On-Premise/Existing Kubernetes** - 🥈 **Simple & Flexible**
- **Best for**: Existing Kubernetes users, compliance requirements, full control
- **Features**: Use your existing cluster, minimal setup, full customization
- **Complexity**: Low (just provide kubeconfig)
- **Cost**: Your existing infrastructure costs
- **Status**: ✅ **Fully tested with existing clusters**

**📖 [On-Premise Deployment Guide](onpremise-deployment.md)**

### 3. **AWS Cloud** - 🥉 **Coming Soon**
- **Best for**: AWS users, EKS clusters, AWS-native services
- **Features**: EKS cluster, RDS, S3 integration
- **Complexity**: Medium (guided CLI deployment)
- **Cost**: Pay-as-you-use AWS resources
- **Status**: 🚧 **In development**

**📖 [AWS Deployment Guide](aws-deployment.md)** *(Coming Soon)*

### 4. **Azure Cloud** - 🥉 **Coming Soon**
- **Best for**: Azure users, AKS clusters, Azure-native services
- **Features**: AKS cluster, Azure Synapse, Blob Storage integration
- **Complexity**: Medium (guided CLI deployment)
- **Cost**: Pay-as-you-use Azure resources
- **Status**: 🚧 **In development**

**📖 [Azure Deployment Guide](azure-deployment.md)** *(Coming Soon)*

## 🚀 Quick Start Decision Tree

```
Do you want to deploy Fast.BI?
├── Yes
│   ├── Do you have an existing Kubernetes cluster?
│   │   ├── Yes → On-Premise Deployment (Simplest)
│   │   └── No → Continue to cloud options
│   │
│   ├── Which cloud provider do you prefer?
│   │   ├── Google Cloud → GCP Deployment (Recommended)
│   │   ├── AWS → AWS Deployment (Coming Soon)
│   │   ├── Azure → Azure Deployment (Coming Soon)
│   │   └── Other → On-Premise with your preferred cloud
│   │
│   └── Do you need full automation?
│       ├── Yes → GCP Deployment (Infrastructure as Code)
│       └── No → On-Premise Deployment (Use existing)
│
└── No → Check out our [demo](https://fast.bi) or [documentation](https://wiki.fast.bi)
```

## 🔧 Prerequisites by Deployment Type

### GCP Deployment
- GCP account with billing enabled
- Organization or folder access
- Domain name for the platform
- Python 3.8+ and kubectl

### On-Premise Deployment
- Existing Kubernetes cluster (1.24+)
- Storage class configured
- Load balancer or ingress controller
- Outbound internet access
- Python 3.8+ and kubectl

### AWS Deployment (Coming Soon)
- AWS account with appropriate permissions
- Domain name for the platform
- Python 3.8+ and kubectl

### Azure Deployment (Coming Soon)
- Azure subscription with appropriate permissions
- Domain name for the platform
- Python 3.8+ and kubectl

## 📋 Common Deployment Phases

All deployment types follow the same 6-phase process:

### Phase 1: Infrastructure
- **GCP**: Create GKE cluster, VPC, load balancer
- **On-Premise**: Validate kubeconfig, check resources
- **AWS/Azure**: Create EKS/AKS cluster, networking

### Phase 2: Secrets
- Generate platform secrets
- Configure authentication
- Set up service accounts

### Phase 3: Repositories
- Configure Git repositories
- Set up access methods
- Verify connectivity

### Phase 4: Infrastructure Services
- Deploy core platform services
- Set up monitoring and logging
- Configure SSO (Keycloak)

### Phase 5: Data Services
- Deploy data platform components
- Configure data pipelines
- Set up BI tools

### Phase 6: Finalization
- Save deployment configuration
- Generate access information
- Complete setup

## 🎯 Choosing Your Deployment Path

### **Start with GCP if you:**
- Want the easiest deployment experience
- Are new to Kubernetes
- Need production-ready infrastructure
- Want full automation
- Are comfortable with Google Cloud

### **Start with On-Premise if you:**
- Already have a Kubernetes cluster
- Need full control over infrastructure
- Have compliance requirements
- Want to minimize cloud costs
- Are experienced with Kubernetes

### **Wait for AWS/Azure if you:**
- Are heavily invested in AWS/Azure
- Need specific AWS/Azure services
- Want to stay within your current cloud ecosystem
- Can wait for full feature parity

## 🚀 Getting Started

1. **Choose your deployment path** using the decision tree above
2. **Review the prerequisites** for your chosen method
3. **Follow the detailed guide** for your deployment type
4. **Use the CLI tool** for guided deployment
5. **Access your platform** and start building data solutions

## 📚 Additional Resources

- **[CLI Documentation](../Infrastructure/bi-platform-docker-images/tsb-fastbi-tenant-web-api-core/cli/README.md)**: Detailed CLI usage
- **[Configuration Examples](../Infrastructure/bi-platform-docker-images/tsb-fastbi-tenant-web-api-core/cli/)**: Sample configuration files
- **[Architecture Overview](architecture.png)**: Platform architecture diagram
- **[Community Support](https://github.com/fast-bi/data-development-platform)**: GitHub discussions and issues

## 🤝 Need Help?

- **Documentation**: Check the specific deployment guide for your chosen method
- **CLI Help**: Run `python cli.py --help` for command options
- **GitHub Issues**: Report bugs or request features
- **Community**: Join discussions and get help from other users

---

**Ready to deploy?** Choose your path above and follow the detailed guide to get started with Fast.BI! 🚀
