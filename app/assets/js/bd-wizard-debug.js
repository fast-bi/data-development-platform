
// Handle page load/refresh
$(document).ready(function() {
  var currentIndex = $('#wizard').steps('getCurrentIndex');
  // Save any items you want to keep
  var itemToKeep = localStorage.getItem('importantItem');
  // Clear all items from localStorage
  localStorage.clear();
  if (localStorage.length === 0) {
    console.log('LocalStorage is empty');
  }
  
  // Verify that localStorage is empty
  for (var i = 0; i < localStorage.length; i++) {
    console.log(`Key ${i}: ${localStorage.key(i)} = ${localStorage.getItem(localStorage.key(i))}`);
    console.log(Object.keys(localStorage)); 
  }
  
  // Restore items you want to keep
  if (itemToKeep) {
      localStorage.setItem('importantItem', itemToKeep);
  }
  setupStepVisibility(currentIndex);
});

// Wizard Init
$("#wizard").steps({
  headerTag: "h3",
  bodyTag: "section",
  transitionEffect: "none",
  stepsOrientation: "vertical",
  titleTemplate: '<span class="number">#index#</span>',
  onInit: function (event, currentIndex) {
      // Initial setup for all steps
      setupStepVisibility(currentIndex);
  },
  onStepChanging: function (event, currentIndex, newIndex) {
      setupStepVisibility(currentIndex);
      // If moving forward from step 1 to step 2
      if (currentIndex === 1 && newIndex === 2) {
          storeCustomerTenantValues();
      }
      return true; // Allow the step change
  },
  onStepChanged: function (event, currentIndex, priorIndex) {
      // Setup visibility for the new step
      setupStepVisibility(currentIndex);
      
      // Load localStorage values when entering step 3 (index 2)
      if (currentIndex === 2) {
        loadLocalStorageValuesStep3();
      }
      // Load localStorage values when entering step 4 (index 3)
      if (currentIndex === 3) {
        loadLocalStorageValuesStep4();
      }
      // Load localStorage values when entering step 5 (index 4)
      if (currentIndex === 4) {
        $('.step-5-only').show();
        loadLocalStorageValuesStep5();
      } else {
        $('.step-5-only').hide();
      }
      if (currentIndex === 6) {
        loadLocalStorageValuesStep7();
      }
      // Load localStorage values when entering step 8 (index 7)
      if (currentIndex === 7) {
        $('.step-8-only').show();
        loadLocalStorageValuesStep8();
      } else {
        $('.step-8-only').hide();
      }
      // Load localStorage values when entering step 9 (index 8)
      if (currentIndex === 8) {
        $('.step-9-only').show();
        loadLocalStorageValuesStep9();
      } else {
        $('.step-9-only').hide();
      }
      // Load localStorage values when entering step 10 (index 9)
      if (currentIndex === 9) {
        $('.step-10-only').show();
        loadLocalStorageValuesStep10();
      } else {
        $('.step-10-only').hide();
      }
  },
  onFinishing: function (event, currentIndex) {
    if (currentIndex === 2) { // We're on the "Generate Tenant Secrets" step
        storeFastBIVaultCredentials();
        
        // Show loading overlay
        $('#loadingOverlayGS').show();
        $('#loadingMessageGS').text('Generating secrets...');
        
        // Disable all wizard buttons to prevent interactions during processing
        $('.actions > ul > li').addClass('disabled');
        
        submitTenantFastBIVaultCredentials()
            .then(function(response) {
                // Update loading message
                $('#loadingMessageGS').text(response.message || 'Secrets generated successfully!');
                
                // Hide loading overlay after a short delay
                setTimeout(function() {
                    $('#loadingOverlayGS').hide();
                    
                    // Enable and show the Next button, hide Finish button
                    $('.actions > ul > li').removeClass('disabled');
                    $('.actions > ul > li:eq(1)').show(); // Show Next button
                    $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
                    
                    // Optionally, you can display the session_id and details
                    console.log('Session ID:', response.session_id);
                    console.log('Details:', response.details);
                }, 1 * 5 * 1000); // 5 second delay
            })
            .catch(function(error) {
                // Update loading message
                $('#loadingMessageGS').text('Error: ' + error);
                
                // Hide loading overlay after a short delay
                setTimeout(function() {
                    $('#loadingOverlayGS').hide();
                    
                    // Re-enable the Finish button
                    $('.actions > ul > li').removeClass('disabled');
                    
                    // Show error message
                    alert('Error: ' + error);
                }, 1 * 60 * 1000); // 1 minutes delay
            });
        
        // Prevent the wizard from finishing automatically
        return false;
    }    
    if (currentIndex === 3) { // We're on the "Deploy Infrastructure" step
      storeFastBIDeploymentInfra();
      
      // Show loading overlay
      $('#loadingOverlayTF').show();
      $('#loadingMessageTF').text('Deploying Infrastructure...');
      
      // Disable all wizard buttons to prevent interactions during processing
      $('.actions > ul > li').addClass('disabled');
      
      submitDeployInfraRequest()
        .then(function(response) {
          // Update loading message
          $('#loadingMessageTF').text(response.message || 'Infrastructure deployed successfully!');
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayTF').hide();
            
            // Enable and show the Next button, hide Finish button
            $('.actions > ul > li').removeClass('disabled');
            $('.actions > ul > li:eq(1)').show(); // Show Next button
            $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
            
            // Optionally, you can display the session_id and details
            console.log('Session ID:', response.session_id);
            console.log('Details:', response.details);
          }, 1 * 5 * 1000); // 5 second delay
        })
        .catch(function(error) {
          // Update loading message
          $('#loadingMessageTF').text('Error: ' + error);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayTF').hide();
            
            // Re-enable the Finish button
            $('.actions > ul > li').removeClass('disabled');
            
            // Show error message
            alert('Error: ' + error);
          }, 1 * 60 * 1000); // 1 minute delay
        });
      
      // Prevent the wizard from finishing automatically
      return false;
    }
    if (currentIndex === 4) { // We're on the "Deploy System Infrastructure Services" step
      storeSystemInfraServices();
      
      // Show loading overlay
      $('#loadingOverlayDSS').show();
      $('#loadingMessageDSS').text('Deploying System Infrastructure Services...');
      
      // Disable all wizard buttons to prevent interactions during processing
      $('.actions > ul > li').addClass('disabled');

      console.log('should start the deployment')
      
      submitDeploySystemInfraServicesRequest()
        .then(function(response) {
          // Update loading message
          $('#loadingMessageDSS').text(response.message || 'System Infrastructure Services deployed successfully!');
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDSS').hide();
            
            // Enable and show the Next button, hide Finish button
            $('.actions > ul > li').removeClass('disabled');
            $('.actions > ul > li:eq(1)').show(); // Show Next button
            $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
            
            console.log('Deployment details:', response.details);
          }, 5000); // 5 second delay
        })
        .catch(function(error) {
          // Update loading message
          $('#loadingMessageDSS').text('Error: ' + error);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDSS').hide();
            
            // Re-enable the Finish button
            $('.actions > ul > li').removeClass('disabled');
            
            // Show error message
            alert('Error: ' + error);
          }, 60000); // 1 minute delay
        });
      
      // Prevent the wizard from finishing automatically
      return false;
    }
    if (currentIndex === 5) { // Step 6 (index 5)
      handleGetRealmConfigurationStep();
    }
    if (currentIndex === 6) { // Step 7 (index 6)
      storeGITProviderCredentials();
        // Show loading overlay
        $('#loadingOverlayGIT').show();
        $('#loadingMessageGS').text('Configuring Data Repository...');
        
        // Disable all wizard buttons to prevent interactions during processing
        $('.actions > ul > li').addClass('disabled');

        submitDataRepositoryConfiguration()
            .then(function(response) {
                // Update loading message
                $('#loadingMessageGS').text(response.message);
                
                // Hide loading overlay after a short delay
                setTimeout(function() {
                    $('#loadingOverlayGIT').hide();
                    
                    // Enable and show the Next button, hide Finish button
                    $('.actions > ul > li').removeClass('disabled');
                    $('.actions > ul > li:eq(1)').show(); // Show Next button
                    $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
                    
                    // Optionally, you can display the session_id and details
                    console.log('Session ID:', response.session_id);
                    console.log('Details:', response.details);
                }, 1 * 5 * 1000); // 5 second delay
            })
            .catch(function(error) {
                // Update loading message
                $('#loadingMessageGS').text('Error: ' + error);
                
                // Hide loading overlay after a short delay
                setTimeout(function() {
                    $('#loadingOverlayGS').hide();
                    
                    // Re-enable the Finish button
                    $('.actions > ul > li').removeClass('disabled');
                    
                    // Show error message
                    alert('Error: ' + error);
                }, 1 * 60 * 1000); // 1 minutes delay
            });
        
        // Prevent the wizard from finishing automatically
        return false;
    }
    if (currentIndex === 7) { // We're on the "Deploy Data Services" step
      storeDataServices();
      
      // Show loading overlay
      $('#loadingOverlayDDS').show();
      $('#loadingMessageDDS').text('Deploying Data Services...');
      
      // Disable all wizard buttons to prevent interactions during processing
      $('.actions > ul > li').addClass('disabled');

      console.log('should start the deployment')
      
      submitDeployDataServicesRequest()
        .then(function(response) {
          // Update loading message
          $('#loadingMessageDDS').text(response.message);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDDS').hide();
            
            // Enable and show the Next button, hide Finish button
            $('.actions > ul > li').removeClass('disabled');
            $('.actions > ul > li:eq(1)').show(); // Show Next button
            $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
            
            console.log('Deployment details:', response.details);
          }, 5000); // 5 second delay
        })
        .catch(function(error) {
          // Update loading message
          $('#loadingMessageDDS').text('Error: ' + error);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDDS').hide();
            
            // Re-enable the Finish button
            $('.actions > ul > li').removeClass('disabled');
            
            // Show error message
            alert('Error: ' + error);
          }, 60000); // 1 minute delay
        });
      
      // Prevent the wizard from finishing automatically
      return false;
    }
    if (currentIndex === 8) { // We're on the "Git Data Repository Finaliser" step
      // Show loading overlay
      $('#loadingOverlayGITFIN').show();
      $('#loadingMessageGITFIN').text('Uploading CI Values...');
      
      // Disable all wizard buttons to prevent interactions during processing
      $('.actions > ul > li').addClass('disabled');
      
      submitGitFinaliserDataRequest()
        .then(function(response) {
          // Update loading message
          $('#loadingOverlayGITFIN').text(response.message);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayGITFIN').hide();
            
            // Enable and show the Next button, hide Finish button
            $('.actions > ul > li').removeClass('disabled');
            $('.actions > ul > li:eq(1)').show(); // Show Next button
            $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
            
            console.log('Deployment details:', response.details);
          }, 5000); // 5 second delay
        })
        .catch(function(error) {
          // Update loading message
          $('#loadingMessageDDS').text('Error: ' + error);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDDS').hide();
            
            // Re-enable the Finish button
            $('.actions > ul > li').removeClass('disabled');
            
            // Show error message
            alert('Error: ' + error);
          }, 60000); // 1 minute delay
        });
      // Prevent the wizard from finishing automatically
      return false;
    }
    if (currentIndex === 9) { // We're on the "Tenant Deploy Finaliser" step
      // Show loading overlay
      $('#loadingOverlayTDF').show();
      $('#loadingMessageTDF').text('Finalising Tenant Deployment...');
      
      // Disable all wizard buttons to prevent interactions during processing
      $('.actions > ul > li').addClass('disabled');
      
      submitTenantDeployFinaliserRequest()
        .then(function(response) {
          // Update loading message
          $('#loadingOverlayTDF').text(response.message);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayTDF').hide();
            
            // Enable and show the Next button, hide Finish button
            $('.actions > ul > li').removeClass('disabled');
            $('.actions > ul > li:eq(0)').hide(); // Hide Previous button
            $('.actions > ul > li:eq(1)').hide(); // Hide Next button
            $('.actions > ul > li:eq(2)').hide(); // Hide Finish button
            console.log('Deployment details:', response.details);
          }, 5000); // 5 second delay
        })
        .catch(function(error) {
          // Update loading message
          $('#loadingMessageDDS').text('Error: ' + error);
          
          // Hide loading overlay after a short delay
          setTimeout(function() {
            $('#loadingOverlayDDS').hide();
            
            // Re-enable the Finish button
            $('.actions > ul > li').removeClass('disabled');
            
            // Show error message
            alert('Error: ' + error);
          }, 60000); // 1 minute delay
        });
      // Prevent the wizard from finishing automatically
      return false;
    }
    return true; // Allow finishing on other steps
  }
});

// Step handling
function setupStepVisibility(stepIndex) {
  // Hide all navigation buttons initially
  $('.actions > ul > li').hide();

  // Hide the confirmation checkbox by default
  $('.step-5-only').hide();

  switch(stepIndex) {
      case 0: // First step (Cloud Provider selection)
          handleCloudProviderStep();
          break;
      case 1: // Second step (Tenant Customer Data)
          $('.actions > ul > li:eq(0)').show(); // Previous button
          var selectedProvider = localStorage.getItem('cloudProvider');
          console.log('Handling provider data:', selectedProvider)
          switch(selectedProvider) {
              case 'gcp':
                  handleTenantCustomerDataStepGCP();
                  break;
              case 'aws':
                  handleTenantCustomerDataStepAWS();
                  break;
              case 'azure':
                  handleTenantCustomerDataStepAzure();
                  break;
              case 'on-premise':
                  handleTenantCustomerDataStepOnPremise();
                  break;
              default:
                  console.error('Unknown cloud provider');
          }
          break;
      case 2: // Third step (Generate Tenant Secrets)
          $('.actions > ul > li:eq(0)').show(); // Previous button
          handleGenerateSecretsStep();
          break;
      case 3: // Fourth step Deploy Tenant Infrastructure
          $('.actions > ul > li:eq(0)').show(); // Previous button
          handleDeployInfraStep();
          break;
      case 4: // Fifth step Deploy System Infrastructure Services
          $('.actions > ul > li:eq(0)').show(); // Previous button
          $('.step-5-only').show(); // Show the confirmation checkbox
          handleDeploySystemInfraServicesStep();
          // $('.actions > ul > li:eq(1)').show(); // Next button
          break;
      case 5: // Sixth step (Get Realm Configuration)
          $('.actions > ul > li:eq(0)').show(); // Previous button
          handleGetRealmConfigurationStep();
          break;
      case 6: // Seventh step (Configure data repository)
          $('.actions > ul > li:eq(0)').show(); // Previous button
          handleGitConfigurationStep();
          break;
      case 7:
          $('.actions > ul > li:eq(0)').show(); // Previous button
          $('.step-8-only').show(); // Show the confirmation checkbox
          handleDeployDataServicesStep();
          //$('.actions > ul > li:eq(1)').show(); // Next button
          break;
      case 8:
          $('.actions > ul > li:eq(0)').show(); // Previous button
          $('.step-9-only').show(); // Show the confirmation checkbox
          handleGitConfigurationFinaliserStep();
          break;
      case 9:
          $('.actions > ul > li:eq(0)').show(); // Previous button
          $('.step-10-only').show(); // Show the confirmation checkbox
          handleTenantDeploymentFinaliserStep();
          break;
      // default:
      //     // For any other steps (if you add more in the future)
      //     $('.actions > ul > li:eq(0)').show(); // Previous button
      //     $('.actions > ul > li:eq(1)').show(); // Next button
      //     break;
  }
}

function handleCloudProviderStep() {
  var selectedProvider = localStorage.getItem('cloudProvider');
  
  // Always hide the Previous button on the first step
  $('.actions > ul > li:eq(0)').hide();
  
  // Show Next button only if a provider is already selected
  if (selectedProvider) {
      $('.actions > ul > li:eq(1)').show();
  } else {
      $('.actions > ul > li:eq(1)').hide();
  }
}


// Shared function for validating Whitelist IPs
function isValidWhitelistIPs(ips) {
  const ipCidrRegex = /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2})(,\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2})*$/;
  return ipCidrRegex.test(ips);
}

// GCP Tenant Customer Data Step Handler
function handleTenantCustomerDataStepGCP() {
  const requiredFields = [
      'tokenKeyValue',
      'gcp-billingAccountID',
      'gcp-orgFolderId',
      'gcp-customerName',
      'gcp-adminEmailAddress',
      'gcp-region',
      'gcp-projectID',
      'gcp-whitelistIPs'
  ];

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
          }
      });

      const whitelistIPs = $('#gcp-whitelistIPs').val().trim();
      if (whitelistIPs && !isValidWhitelistIPs(whitelistIPs)) {
          isValid = false;
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(1)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('input[data-provider="gcp"]').on('input', updateNextButtonVisibility);

  // Special handling for whitelist IPs
  $('#gcp-whitelistIPs').on('input', function() {
      const value = $(this).val().trim();
      if (value && !isValidWhitelistIPs(value)) {
          $(this).addClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('Invalid IP/CIDR format');
      } else {
          $(this).removeClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('');
      }
      updateNextButtonVisibility();
  });
}

// AWS Tenant Customer Data Step Handler
function handleTenantCustomerDataStepAWS() {
  const requiredFields = [
      'aws-billingAccountID',
      'aws-customerName',
      'aws-adminEmailAddress',
      'aws-region',
      'aws-whitelistIPs'
  ];

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
          }
      });

      const whitelistIPs = $('#aws-whitelistIPs').val().trim();
      if (whitelistIPs && !isValidWhitelistIPs(whitelistIPs)) {
          isValid = false;
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(1)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('input[data-provider="aws"]').on('input', updateNextButtonVisibility);

  // Special handling for whitelist IPs
  $('#aws-whitelistIPs').on('input', function() {
      const value = $(this).val().trim();
      if (value && !isValidWhitelistIPs(value)) {
          $(this).addClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('Invalid IP/CIDR format');
      } else {
          $(this).removeClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('');
      }
      updateNextButtonVisibility();
  });
}

// Azure Tenant Customer Data Step Handler
function handleTenantCustomerDataStepAzure() {
  const requiredFields = [
      'azure-billingAccountID',
      'azure-customerName',
      'azure-adminEmailAddress',
      'azure-region',
      'azure-whitelistIPs'
  ];

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
          }
      });

      const whitelistIPs = $('#azure-whitelistIPs').val().trim();
      if (whitelistIPs && !isValidWhitelistIPs(whitelistIPs)) {
          isValid = false;
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(1)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('input[data-provider="azure"]').on('input', updateNextButtonVisibility);

  // Special handling for whitelist IPs
  $('#azure-whitelistIPs').on('input', function() {
      const value = $(this).val().trim();
      if (value && !isValidWhitelistIPs(value)) {
          $(this).addClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('Invalid IP/CIDR format');
      } else {
          $(this).removeClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('');
      }
      updateNextButtonVisibility();
  });
}

// On-Premises Tenant Customer Data Step Handler
function handleTenantCustomerDataStepOnPremise() {
  const requiredFields = [
      'on-premise-customerName',
      'on-premise-adminEmailAddress',
      'on-premise-k8s-endpoint',
      'on-premise-whitelistIPs'
  ];

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
          }
      });

      const whitelistIPs = $('#on-premise-whitelistIPs').val().trim();
      if (whitelistIPs && !isValidWhitelistIPs(whitelistIPs)) {
          isValid = false;
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(1)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('input[data-provider="on-premise"]').on('input', updateNextButtonVisibility);

  // Special handling for whitelist IPs
  $('#on-premise-whitelistIPs').on('input', function() {
      const value = $(this).val().trim();
      if (value && !isValidWhitelistIPs(value)) {
          $(this).addClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('Invalid IP/CIDR format');
      } else {
          $(this).removeClass('is-invalid');
          $(this).siblings('.invalid-feedback').text('');
      }
      updateNextButtonVisibility();
  });
}

// Function to handle the Generate Secret step
function handleGenerateSecretsStep() {
  const requiredFields = [
      'vaultClientId',
      'vaultClientSecret'
  ];

  function isValidUUID(uuid) {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      return uuidRegex.test(uuid);
  }

  function isValidSecret(secret) {
      const secretRegex = /^[0-9a-f]{64}$/i;
      return secretRegex.test(secret);
  }

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
          }
      });

      const clientId = $('#vaultClientId').val().trim();
      const clientSecret = $('#vaultClientSecret').val().trim();

      if (!isValidUUID(clientId)) {
          isValid = false;
          $('#vaultClientId').addClass('is-invalid');
          $('#vaultClientId').siblings('.invalid-feedback').text('Invalid Client ID format');
      } else {
          $('#vaultClientId').removeClass('is-invalid');
          $('#vaultClientId').siblings('.invalid-feedback').text('');
      }

      if (!isValidSecret(clientSecret)) {
          isValid = false;
          $('#vaultClientSecret').addClass('is-invalid');
          $('#vaultClientSecret').siblings('.invalid-feedback').text('Invalid Client Secret format');
      } else {
          $('#vaultClientSecret').removeClass('is-invalid');
          $('#vaultClientSecret').siblings('.invalid-feedback').text('');
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(2)').show(); // Show Finish button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('#vaultClientId, #vaultClientSecret').on('input', updateNextButtonVisibility);
}

// Function to handle the Deploy Infrastructure step
function handleDeployInfraStep() {
  const requiredFields = [
      'deploymentType',
      'confirmationCheckbox'
  ];

  function checkFormValidity() {
      let isValid = true;
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length) {
              if (field.attr('type') === 'checkbox') {
                  if (!field.prop('checked')) {
                      isValid = false;
                  }
              } else if (!field.val().trim()) {
                  isValid = false;
              }
          }
      });

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(2)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(2)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners
  $('#confirmationTFCheckbox').on('change', updateNextButtonVisibility);
}

// Step 0 Cloud provider selection 
$('.purpose-radio').on('click', function() {
  var selectedProvider = $(this).attr('data-provider');
  var selectedProviderDWH = $(this).attr('data-service');
  localStorage.setItem('cloudProvider', selectedProvider);
  localStorage.setItem('cloudProviderDWH', selectedProviderDWH);

  // Show the Next button when a provider is selected
  $('.actions > ul > li:eq(1)').show();

  console.log('Selected provider:', selectedProvider);
  console.log('Selected provider DWH:', selectedProviderDWH);
});

// Store Index 1 values when moving to the next step
function storeCustomerTenantValues() {
  var cloudProvider = localStorage.getItem('cloudProvider');
  
  // Store values based on the selected cloud provider
  if (cloudProvider === 'gcp') {
    localStorage.setItem('tokenKey', $('#tokenKeyValue').val());
    localStorage.setItem('billingAccountId', $('#gcp-billingAccountID').val());
    localStorage.setItem('orgFolderId', $('#gcp-orgFolderId').val());
    localStorage.setItem('customerName', $('#gcp-customerName').val());
    localStorage.setItem('ownerEmail', $('#gcp-adminEmailAddress').val());
    localStorage.setItem('region', $('#gcp-region').val());
    localStorage.setItem('projectId', $('#gcp-projectID').val());
    localStorage.setItem('whitelistIPs', $('#gcp-whitelistIPs').val());
  } else if (cloudProvider === 'aws') {
    localStorage.setItem('billingAccountId', $('#aws-billingAccountID').val());
    localStorage.setItem('customerName', $('#aws-customerName').val());
    localStorage.setItem('ownerEmail', $('#aws-adminEmailAddress').val());
    localStorage.setItem('region', $('#aws-region').val());
    localStorage.setItem('whitelistIPs', $('#aws-whitelistIPs').val());
  } else if (cloudProvider === 'azure') {
    localStorage.setItem('billingAccountId', $('#azure-billingAccountID').val());
    localStorage.setItem('customerName', $('#azure-customerName').val());
    localStorage.setItem('ownerEmail', $('#azure-adminEmailAddress').val());
    localStorage.setItem('region', $('#azure-region').val());
    localStorage.setItem('whitelistIPs', $('#azure-whitelistIPs').val());
  } else if (cloudProvider === 'on-premise') {
    localStorage.setItem('customerName', $('#on-premise-customerName').val());
    localStorage.setItem('ownerEmail', $('#on-premise-adminEmailAddress').val());
    localStorage.setItem('kubernetesEndpoint', $('#on-premise-k8s-endpoint').val());
    localStorage.setItem('whitelistIPs', $('#on-premise-whitelistIPs').val());
  }

  // Debug
  // Show in log if the fields were filled.
  console.log('Step 2 values stored:', {
    cloudProvider: cloudProvider,
    tokenKey: localStorage.getItem('tokenKey'),
    billingAccountId: localStorage.getItem('billingAccountId'),
    customerName: localStorage.getItem('customerName'),
    ownerEmail: localStorage.getItem('ownerEmail'),
    region: localStorage.getItem('region'),
    projectId: localStorage.getItem('projectId'),
    whitelistIPs: localStorage.getItem('whitelistIPs'),
    kubernetesEndpoint: localStorage.getItem('kubernetesEndpoint')
  });
}

// Store Index 2 load values, store Vault Credentials, submit the Generate Secrets.
function loadLocalStorageValuesStep3() {
  const customerName = localStorage.getItem('customerName');
  const ownerEmail = localStorage.getItem('ownerEmail');
  
  console.log(`Loading values from step 2 for step 3:
    customerName: ${customerName},
    ownerEmail: ${ownerEmail}`);
  
  // Populate the fields in the review section
  $('#reviewCustomerName').text(customerName || 'N/A');
  $('#reviewEmail').text(ownerEmail || 'N/A');
}

function storeFastBIVaultCredentials() {
  localStorage.setItem('vaultClientId', $('#vaultClientId').val());
  localStorage.setItem('vaultClientSecret', $('#vaultClientSecret').val());

  // Debug
  // Show in log if the vault client fields were filled
  console.log('Step 3 values stored:', {
    cloudProvider: localStorage.getItem('cloudProvider'),
    customerName: localStorage.getItem('customerName'),
    ownerEmail: localStorage.getItem('ownerEmail'),
    vaultClientId: localStorage.getItem('vaultClientId'),
    vaultClientSecret: localStorage.getItem('vaultClientSecret')
  });
}

function submitTenantFastBIVaultCredentials() {
  var data = {
      client_id: localStorage.getItem('vaultClientId'),
      client_secret: localStorage.getItem('vaultClientSecret'),
      customer: localStorage.getItem('customerName'),
      user_email: localStorage.getItem('ownerEmail')
  };
  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();

  return $.ajax({
      url: '/api/v1/create-customer-vault',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "Bearer " + window.bearerToken  // We'll set this from Flask
      }
  }).then(function(response) {
      var endTime = new Date().getTime();
      var duration = endTime - startTime;
      
      console.log('API response:', response);
      console.log('Request duration:', duration, 'ms');
      return response;
  }).fail(function(xhr, status, error) {
      var endTime = new Date().getTime();
      var duration = endTime - startTime;

      console.error('API error:', error);
      console.log('Request duration:', duration, 'ms');
      throw error;
  });
}

// Load existing values for Deploy Infrastructure step
function loadLocalStorageValuesStep4() {
  const tokenKey = localStorage.getItem('tokenKey');
  const cloudProvider = localStorage.getItem('cloudProvider');
  const billingAccountId = localStorage.getItem('billingAccountId');
  const orgFolderId = localStorage.getItem('orgFolderId');
  const customerName = localStorage.getItem('customerName');
  const ownerEmail = localStorage.getItem('ownerEmail');
  const region = localStorage.getItem('region');
  const projectId = localStorage.getItem('projectId');
  const whitelistIPs = localStorage.getItem('whitelistIPs');
  
  console.log(`Loading values from step 2 for step 4:
    tokenKey: ${tokenKey},
    cloudProvider: ${cloudProvider},
    billingAccountId: ${billingAccountId},
    orgFolderId: ${orgFolderId},
    customerName: ${customerName},
    ownerEmail: ${ownerEmail},
    region: ${region},
    projectId: ${projectId},
    whitelistIPs: ${whitelistIPs}`);
  
  // Populate the fields in the review section
  $('#reviewTFCloudProvider').text(cloudProvider || 'N/A');
  $('#reviewTFTokenKey').text(tokenKey || 'N/A');
  $('#reviewTFBillingAccount').text(billingAccountId || 'N/A');
  $('#reviewTForgFolderId').text(orgFolderId || 'N/A');
  $('#reviewTFRegion').text(region || 'N/A');
  $('#reviewProjectID').text(projectId || 'N/A');
  $('#reviewTFCustomerName').text(customerName || 'N/A');
  $('#reviewTFEmail').text(ownerEmail || 'N/A');
  $('#reviewTFWhitelistIPs').text(whitelistIPs || 'N/A');
}

// Store Deploy Infrastructure values
function storeFastBIDeploymentInfra() {
  localStorage.setItem('deploymentType', $('#deploymentType').val());

  // Debug
  // Show in log if the deployment type field was filled
  console.log('Deploy Infrastructure values stored:', {
    cloudProvider: localStorage.getItem('cloudProvider'),
    tokenKey: localStorage.getItem('tokenKey'),
    billingAccountId: localStorage.getItem('billingAccountId'),
    orgFolderId: localStorage.getItem('orgFolderId'),
    customerName: localStorage.getItem('customerName'),
    ownerEmail: localStorage.getItem('ownerEmail'),
    region: localStorage.getItem('region'),
    projectId: localStorage.getItem('projectId'),
    whitelistIPs: localStorage.getItem('whitelistIPs'),
    deploymentType: localStorage.getItem('deploymentType')
  });
}

// Function to submit Deploy Infrastructure request
function submitDeployInfraRequest() {
  var data = {
    cloud_provider: localStorage.getItem('cloudProvider'),
    deployment: localStorage.getItem('deploymentType'),
    billing_account_id: localStorage.getItem('billingAccountId'),
    parent_folder: localStorage.getItem('orgFolderId'),
    customer: localStorage.getItem('customerName'),
    admin_email: localStorage.getItem('ownerEmail'),
    region: localStorage.getItem('region'),
    project_id: localStorage.getItem('projectId'),
    whitelisted_ips: [localStorage.getItem('whitelistIPs')]
  };
  var header_token_key = localStorage.getItem('tokenKey')

  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();

  return $.ajax({
    url: '/api/v1/deploy/infra-environment',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
    headers: {
      "accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": "Bearer " + window.bearerToken,  // We'll set this from Flask
      "X-Token-Key": header_token_key
    }
  }).then(function(response) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;
    
    console.log('API response:', response);
    console.log('Request duration:', duration, 'ms');
    return response;
  }).fail(function(xhr, status, error) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;

    console.error('API error:', error);
    console.log('Request duration:', duration, 'ms');
    throw error;
  });
}

// Store System Infrastructure Services selections
function storeSystemInfraServices() {
  const serviceVersions = {};
  $('#systemInfraServicesForm select').each(function() {
    const serviceName = $(this).attr('name');
    const selectedVersion = $(this).val();
    serviceVersions[serviceName] = selectedVersion;
  });
  localStorage.setItem('systemInfraServiceVersions', JSON.stringify(serviceVersions));

  // Debug: Log the stored values
  console.log('Stored System Infra Service Versions:', serviceVersions);
}

// Load existing values for Deploy System Infrastructure Services step
function loadLocalStorageValuesStep5() {
  const tokenKey = localStorage.getItem('tokenKey');
  const cloudProvider = localStorage.getItem('cloudProvider');
  const customerName = localStorage.getItem('customerName');
  const ownerEmail = localStorage.getItem('ownerEmail');
  const region = localStorage.getItem('region');
  const projectId = localStorage.getItem('projectId');
  const whitelistIPs = localStorage.getItem('whitelistIPs');
  const externalDNS = localStorage.getItem('externalDNS') || `${customerName}.fast.bi`;
  
  console.log(`Loading values for Deploy System Infrastructure Services step:
    tokenKey: ${tokenKey},
    cloudProvider: ${cloudProvider},
    customerName: ${customerName},
    ownerEmail: ${ownerEmail},
    region: ${region},
    projectId: ${projectId},
    whitelistIPs: ${whitelistIPs},
    externalDNS: ${externalDNS}`);
  
  // Populate the fields in the review section
  $('#reviewDSSCloudProvider').text(cloudProvider || 'N/A');
  $('#reviewDSSTokenKey').text(tokenKey || 'N/A');
  $('#reviewDSSRegion').text(region || 'N/A');
  $('#reviewDSSProjectID').text(projectId || 'N/A');
  $('#reviewDSSCustomerName').text(customerName || 'N/A');
  $('#reviewDSSExternalDNS').text(externalDNS || 'N/A');
  $('#reviewDSSEmail').text(ownerEmail || 'N/A');
  $('#reviewDSSWhitelistIPs').text(whitelistIPs || 'N/A');

  // Load and display stored system infra service versions
  const storedVersions = JSON.parse(localStorage.getItem('systemInfraServiceVersions') || '{}');
  for (const [serviceName, version] of Object.entries(storedVersions)) {
    $(`#${serviceName}`).val(version);
  }
}

// Handle Deploy System Infrastructure Services step
function handleDeploySystemInfraServicesStep() {
  function checkFormValidity() {
    return $('#confirmationDSSCheckbox').is(':checked');
  }

  function updateNextButtonVisibility() {
    if (checkFormValidity()) {
      $('.actions > ul > li:eq(2)').show(); // Show Next button
      storeSystemInfraServices(); // Store the selected versions when the form is valid
    } else {
      $('.actions > ul > li:eq(1)').hide(); // Hide Next button
    }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listener to the confirmation checkbox
  $('#confirmationDSSCheckbox').off('change').on('change', updateNextButtonVisibility);

  // Optional: Add event listeners to all select fields to remind user to confirm
  $('#systemInfraServicesForm select').off('change').on('change', function() {
    if ($('#confirmationDSSCheckbox').is(':checked')) {
      $('#confirmationDSSCheckbox').prop('checked', false);
      updateNextButtonVisibility();
    }
  });
}

// Function to submit Deploy System Infrastructure Services request
function submitDeploySystemInfraServicesRequest() {
  const storedVersions = JSON.parse(localStorage.getItem('systemInfraServiceVersions') || '{}');
  const customerName = localStorage.getItem('customerName');
  const externalDNS = localStorage.getItem('externalDNS') || `${customerName}.fast.bi`;
  
  const data = {
    cloud_provider: localStorage.getItem('cloudProvider'),
    customer: localStorage.getItem('customerName'),
    user_email: localStorage.getItem('ownerEmail'),
    region: localStorage.getItem('region'),
    project_id: localStorage.getItem('projectId'),
    whitelisted_environment_ips: [localStorage.getItem('whitelistIPs')],
    external_dns_domain_filters: [externalDNS],
    secret_operator_chart_version: storedVersions['infisical/secrets-operator'] || '',
    cert_manager_chart_version: storedVersions['jetstack/cert-manager'] || '',
    external_dns_chart_version: storedVersions['bitnami/external-dns'] || '',
    traefik_chart_version: storedVersions['traefik/traefik'] || '',
    keycloak_chart_version: storedVersions['bitnami/keycloak'] || '',
    object_storage_chart_version: storedVersions['minio/tenant'] || '',
    object_storage_operator_chart_version: storedVersions['minio/operator'] || '',
    prometheus_chart_version: storedVersions['prometheus_community/prometheus'] || '',
    grafana_chart_version: storedVersions['grafana/grafana'] || '',
    kube_cleanup_operator_chart_version: storedVersions['lwolf_charts/kube-cleanup-operator'] || ''
  };

  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();
  var header_token_key = localStorage.getItem('tokenKey');

  return $.ajax({
    url: '/api/v1/deploy/infra-services',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
    headers: {
      "accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": "Bearer " + window.bearerToken,
      "X-Token-Key": header_token_key
    }
  }).then(function(response) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;
    
    console.log('API response:', response);
    console.log('Request duration:', duration, 'ms');
    return response;
  }).fail(function(xhr, status, error) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;

    console.error('API error:', error);
    console.log('Request duration:', duration, 'ms');
    throw error;
  });
}

function handleGetRealmConfigurationStep() {
  // Retrieve customer name from localStorage
  const customerName = localStorage.getItem('customerName');

  // Disable the Next button initially
  $('.actions > ul > li:eq(1)').hide();

  // Display customer name and add a button to fetch realm configuration
  $('#realmConfigurationContent').html(`
      <h4>Get Realm Configuration for ${customerName}</h4>
      <button id="fetchRealmConfigBtn" class="btn btn-primary">Fetch Realm Configuration</button>
      <div id="realmConfigResult" style="display:none;"></div>
  `);

  // Add click event to the fetch button
  $('#fetchRealmConfigBtn').on('click', function() {
      fetchRealmConfiguration(customerName);
  });

  // We'll add the checkbox event listener here, but it won't do anything until the checkbox exists
  $(document).on('change', '#realmConfigUploadedCheckbox', function() {
      if ($(this).is(':checked')) {
          $('.actions > ul > li:eq(1)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  });
}

function fetchRealmConfiguration(customerName) {
  const data = { customer: customerName };
  
  $.ajax({
      url: '/api/v1/get/idp-sso-realm',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "Bearer " + window.bearerToken
      }
  }).then(function(response) {
      displayRealmConfiguration(response);
  }).fail(function(xhr, status, error) {
      $('#realmConfigResult').html(`<p class="text-danger">Error fetching realm configuration: ${error}</p>`);
      $('#realmConfigResult').show();
  });
}

function displayRealmConfiguration(config) {
  const resultHtml = `
      <div class="mt-4">
          <p><strong>Customer:</strong> ${config.customer}</p>
          <p><strong>IDP SSO Credentials:</strong> <a href="${config.customer_idp_sso_credentials_url}" target="_blank">Click here to view (one-time link)</a></p>
          <p><strong>IDP Console Endpoint:</strong> <a href="${config.idp_console_endpoint_url}" target="_blank">${config.idp_console_endpoint_url}</a></p>
          <p><strong>Message:</strong> ${config.message}</p>
          <p><strong>Realm Configuration File:</strong> <a href="${config.realm_configuration_file_url}" download>Download Configuration File</a></p>
      </div>
      <div class="form-group mt-4">
          <div class="custom-control custom-checkbox">
              <input type="checkbox" class="custom-control-input" id="realmConfigUploadedCheckbox">
              <label class="custom-control-label" for="realmConfigUploadedCheckbox">I confirm that I have downloaded the configuration file and uploaded it to the IDP console.</label>
          </div>
      </div>
  `;

  $('#realmConfigResult').html(resultHtml);
  $('#realmConfigResult').show();
  $('#fetchRealmConfigBtn').hide();

  // Ensure the Next button is hidden when the configuration is displayed
  $('.actions > ul > li:eq(1)').hide();
}

// Store Index 6 load values, store Git Operator Access token, submit the data repository configuration.
function loadLocalStorageValuesStep7() {
  const cloud_provider = localStorage.getItem('cloudProvider');
  const customer_name = localStorage.getItem('customerName');
  const project_id = localStorage.getItem('projectId');
  
  console.log(`Loading values from step 2 for step 7:
    cloud_provider: ${cloud_provider},
    customerName: ${customer_name},
    project_id: ${project_id}`);

  
  // Populate the fields in the review section
  $('#reviewGITCloudProvider').text(cloud_provider || 'N/A');
  $('#reviewGITCustomerName').text(customer_name || 'N/A');
  $('#reviewGITProjectID').text(project_id || 'N/A');
}

function storeGITProviderCredentials() {
  localStorage.setItem('repoProviderType', $('#repoProviderType').val());
  localStorage.setItem('fastbiCICDVersion', $('#fastbiCICDVersion').val());
  localStorage.setItem('repoGitGlobalAccessToken', $('#repoGitGlobalAccessToken').val());

  // Debug
  // Show in log if the vault client fields were filled
  console.log('Step 7 values stored:', {
    cloudProvider: localStorage.getItem('cloudProvider'),
    customerName: localStorage.getItem('customerName'),
    projectID: localStorage.getItem('projectId'),
    repoProviderType: localStorage.getItem('repoProviderType'),
    fastbiCICDVersion: localStorage.getItem('fastbiCICDVersion'),
    repoGitGlobalAccessToken: localStorage.getItem('repoGitGlobalAccessToken')
  });
}

function submitDataRepositoryConfiguration() {
  var data = {
      customer: localStorage.getItem('customerName'),
      project_id: localStorage.getItem('projectId'),
      git_provider: localStorage.getItem('repoProviderType'),
      git_access_token: localStorage.getItem('repoGitGlobalAccessToken'),
      fast_bi_cicd_version: localStorage.getItem('fastbiCICDVersion')
  };
  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();

  return $.ajax({
      url: '/api/v1/deploy/data-repo-service',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "Bearer " + window.bearerToken  // We'll set this from Flask
      }
  }).then(function(response) {
      var endTime = new Date().getTime();
      var duration = endTime - startTime;
      
      console.log('API response:', response);
      console.log('Request duration:', duration, 'ms');
      return response;
  }).fail(function(xhr, status, error) {
      var endTime = new Date().getTime();
      var duration = endTime - startTime;

      console.error('API error:', error);
      console.log('Request duration:', duration, 'ms');
      throw error;
  });
}

// Function to handle the Repo Configuration step
function handleGitConfigurationStep() {
  const requiredFields = [
      'repoProviderType',
      'fastbiCICDVersion',
      'repoGitGlobalAccessToken'
  ];

  function isValidCICDVersion(version) {
      const versionRegex = /^v.+$/;
      return versionRegex.test(version);
  }

  function isValidAccessToken(token) {
      const tokenRegex = /^[^\s"'`]+$/;
      return tokenRegex.test(token);
  }

  function checkFormValidity() {
      let isValid = true;

      // Check required fields
      requiredFields.forEach(fieldId => {
          const field = $(`#${fieldId}`);
          if (field.length && field.prop('required') && !field.val().trim()) {
              isValid = false;
              field.addClass('is-invalid');
              field.siblings('.invalid-feedback').text('This field is required');
          } else {
              field.removeClass('is-invalid');
              field.siblings('.invalid-feedback').text('');
          }
      });

      const cicdVersion = $('#fastbiCICDVersion').val().trim();
      const accessToken = $('#repoGitGlobalAccessToken').val().trim();

      // Validate FastBI CICD Version
      if (!isValidCICDVersion(cicdVersion)) {
          isValid = false;
          $('#fastbiCICDVersion').addClass('is-invalid');
          $('#fastbiCICDVersion').siblings('.invalid-feedback').text('Version must start with "v"');
      } else {
          $('#fastbiCICDVersion').removeClass('is-invalid');
          $('#fastbiCICDVersion').siblings('.invalid-feedback').text('');
      }

      // Validate Access Token
      if (!isValidAccessToken(accessToken)) {
          isValid = false;
          $('#repoGitGlobalAccessToken').addClass('is-invalid');
          $('#repoGitGlobalAccessToken').siblings('.invalid-feedback').text('Access Token cannot contain spaces or quotes');
      } else {
          $('#repoGitGlobalAccessToken').removeClass('is-invalid');
          $('#repoGitGlobalAccessToken').siblings('.invalid-feedback').text('');
      }

      return isValid;
  }

  function updateNextButtonVisibility() {
      if (checkFormValidity()) {
          $('.actions > ul > li:eq(2)').show(); // Show Next button
      } else {
          $('.actions > ul > li:eq(1)').hide(); // Hide Next button
      }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listeners to all form fields
  $('#repoProviderType, #fastbiCICDVersion, #repoGitGlobalAccessToken').on('input', updateNextButtonVisibility);
}

// Store System Infrastructure Services selections
function storeDataServices() {
  const serviceVersions = {};
  $('#dataAndFastbiServicesForm select').each(function() {
    const serviceName = $(this).attr('name');
    const selectedVersion = $(this).val();
    serviceVersions[serviceName] = selectedVersion;
  });
  localStorage.setItem('dataServiceVersions', JSON.stringify(serviceVersions));
  localStorage.setItem('dataVisualisationType', $('#dataVisualisationType').val());
  localStorage.setItem('dataDestinationType', $('#dataDestinationType').val());

  // Debug: Log the stored values
  console.log('Stored Data Service Versions:', serviceVersions);
}

// Load existing values for Deploy System Infrastructure Services step
function loadLocalStorageValuesStep8() {
  const tokenKey = localStorage.getItem('tokenKey');
  const cloudProvider = localStorage.getItem('cloudProvider');
  const customerName = localStorage.getItem('customerName');
  const ownerEmail = localStorage.getItem('ownerEmail');
  const region = localStorage.getItem('region');
  const projectId = localStorage.getItem('projectId');
  const whitelistIPs = localStorage.getItem('whitelistIPs');
  const externalDNS = localStorage.getItem('externalDNS') || `${customerName}.fast.bi`;
  const repoProviderType = localStorage.getItem('repoProviderType');
  
  console.log(`Loading values for Deploy System Infrastructure Services step:
    tokenKey: ${tokenKey},
    cloudProvider: ${cloudProvider},
    customerName: ${customerName},
    ownerEmail: ${ownerEmail},
    region: ${region},
    projectId: ${projectId},
    whitelistIPs: ${whitelistIPs},
    externalDNS: ${externalDNS},
    repoProviderType: ${repoProviderType}`);
  
  // Populate the fields in the review section
  $('#reviewDDSCloudProvider').text(cloudProvider || 'N/A');
  $('#reviewDDSTokenKey').text(tokenKey || 'N/A');
  $('#reviewDDSRegion').text(region || 'N/A');
  $('#reviewDDSProjectID').text(projectId || 'N/A');
  $('#reviewDDSCustomerName').text(customerName || 'N/A');
  $('#reviewDDSExternalDNS').text(externalDNS || 'N/A');
  $('#reviewDDSEmail').text(ownerEmail || 'N/A');
  $('#reviewDDSWhitelistIPs').text(whitelistIPs || 'N/A');
  $('#reviewDDSRepoProvider').text(repoProviderType || 'N/A');

  // Load and display stored system infra service versions
  const storedVersions = JSON.parse(localStorage.getItem('dataServiceVersions') || '{}');
  for (const [serviceName, version] of Object.entries(storedVersions)) {
    $(`#${serviceName}`).val(version);
  }
}

// Handle Deploy System Infrastructure Services step
function handleDeployDataServicesStep() {
  function checkFormValidity() {
    return $('#confirmationDDSCheckbox').is(':checked');
  }

  function updateNextButtonVisibility() {
    if (checkFormValidity()) {
      $('.actions > ul > li:eq(2)').show(); // Show Next button
      storeDataServices(); // Store the selected versions when the form is valid
    } else {
      $('.actions > ul > li:eq(1)').hide(); // Hide Next button
    }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listener to the confirmation checkbox
  $('#confirmationDDSCheckbox').off('change').on('change', updateNextButtonVisibility);

  // Optional: Add event listeners to all select fields to remind user to confirm
  $('#dataAndFastbiServicesForm select').off('change').on('change', function() {
    if ($('#confirmationDDSCheckbox').is(':checked')) {
      $('#confirmationDDSCheckbox').prop('checked', false);
      updateNextButtonVisibility();
    }
  });
}

// Function to submit Deploy System Infrastructure Services request
function submitDeployDataServicesRequest() {
  const storedVersions = JSON.parse(localStorage.getItem('dataServiceVersions') || '{}');
  const customerName = localStorage.getItem('customerName');
  const externalDNS = localStorage.getItem('externalDNS') || `${customerName}.fast.bi`;
  //const dataVisualisationType = localStorage.getItem('dataVisualisationType');
  //const dataDestinationType = localStorage.getItem('dataDestinationType');
  //const repoProviderType = localStorage.getItem('repoProviderType');
  
  const data = {
    cloud_provider: localStorage.getItem('cloudProvider'),
    customer: localStorage.getItem('customerName'),
    project_id: localStorage.getItem('projectId'),
    region: localStorage.getItem('region'),
    user_email: localStorage.getItem('ownerEmail'),
    git_provider: localStorage.getItem('repoProviderType'),
    data_replication_default_destination_type: localStorage.getItem('dataDestinationType'),
    tsb_fastbi_web_core_image_version: `bi-platform/tsb-fastbi-web-core:${storedVersions['bi-platform/tsb-fastbi-web-core'] || ''}`,
    tsb_dbt_init_core_image_version: `bi-platform/tsb-dbt-init-core:${storedVersions['bi-platform/tsb-dbt-init-core'] || ''}`,
    dcdq_metacollect_app_version: `bi-platform/tsb-fastbi-meta-api-core:${storedVersions['bi-platform/tsb-fastbi-meta-api-core'] || ''}`,
    gitlab_runner_chart_version: storedVersions['gitlab/gitlab-runner'] || '',
    airbyte_oss_chart_version: storedVersions['airbyte/airbyte'] || '',
    airflow_chart_version: storedVersions['airflow/airflow'] || '',
    airflow_app_version: storedVersions['airflow/airflow/app'] || '',
    datahub_chart_version: storedVersions['datahub/datahub'] || '',
    datahub_prereq_chart_version: storedVersions['datahub/datahub-prerequisites'] || '',
    datahub_eck_es_op_chart_version: storedVersions['elastic/eck-operator'] || '',
    datahub_eck_es_chart_version: storedVersions['elastic/eck-elasticsearch'] || '',
    jupyterhub_chart_version: storedVersions['jupyterhub/jupyterhub'] || '',
    jupyterhub_app_version: storedVersions['jupyterhub/jupyterhub/app'] || '',
    bi_system: localStorage.getItem('dataVisualisationType'),
    superset_chart_version: storedVersions['superset/superset'] || '',
    superset_app_version: storedVersions['superset/superset/app'] || '',
    lightdash_app_version: storedVersions['lightdash/lightdash/app'] || '',
    lightdash_chart_version: storedVersions['lightdash/lightdash'] || '',
    metabase_app_version: storedVersions['metabase/metabase/app'] || '',
    metabase_chart_version: storedVersions['metabase/metabase'] || ''
  };

  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();
  var header_token_key = localStorage.getItem('tokenKey');

  return $.ajax({
    url: '/api/v1/deploy/data-services',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
    headers: {
      "accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": "Bearer " + window.bearerToken,
      "X-Token-Key": header_token_key
    }
  }).then(function(response) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;
    
    console.log('API response:', response);
    console.log('Request duration:', duration, 'ms');
    return response;
  }).fail(function(xhr, status, error) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;

    console.error('API error:', error);
    console.log('Request duration:', duration, 'ms');
    throw error;
  });
}

// Load existing values for Git Repo CI values upload  step
function loadLocalStorageValuesStep9() {
  const cloudProvider = localStorage.getItem('cloudProvider');
  const customerName = localStorage.getItem('customerName');
  const projectId = localStorage.getItem('projectId');
  const repoProviderType = localStorage.getItem('repoProviderType');
  const dataVisualisationType = localStorage.getItem('dataVisualisationType');
  const dataOrchestrationType = 'Airflow'
  
  console.log(`Loading values for for Git Repo CI values upload step:
    cloudProvider: ${cloudProvider},
    customerName: ${customerName},
    projectId: ${projectId},
    repoProviderType: ${repoProviderType},
    dataVisualisationType: ${dataVisualisationType},
    dataOrchestrationType: ${dataOrchestrationType}`);
  
  // Populate the fields in the review section
  $('#reviewGITFINCloudProvider').text(cloudProvider || 'N/A');
  $('#reviewGITFINProjectID').text(projectId || 'N/A');
  $('#reviewGITFINCustomerName').text(customerName || 'N/A');
  $('#reviewGITFINgitProvider').text(repoProviderType || 'N/A');
  $('#reviewGITFINdataAnalysis').text(dataVisualisationType || 'N/A');
  $('#reviewGITFINdataOrchestration').text(dataOrchestrationType || 'N/A');
}

// Handle Git Repo finaliser step
function handleGitConfigurationFinaliserStep() {
  function checkFormValidity() {
    return $('#confirmationGITFINCheckbox').is(':checked');
  }

  function updateNextButtonVisibility() {
    if (checkFormValidity()) {
      $('.actions > ul > li:eq(2)').show(); // Show Next button
      //....
    } else {
      $('.actions > ul > li:eq(1)').hide(); // Hide Next button
    }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listener to the confirmation checkbox
  $('#confirmationGITFINCheckbox').off('change').on('change', updateNextButtonVisibility);
}

// Function to submit Git Repo Finaliser request
function submitGitFinaliserDataRequest() {  
  const data = {
    cloud_provider: localStorage.getItem('cloudProvider'),
    customer: localStorage.getItem('customerName'),
    project_id: localStorage.getItem('projectId'),
    git_provider: localStorage.getItem('repoProviderType'),
    bi_system: localStorage.getItem('dataVisualisationType'),
    data_orchestrator_platform: 'Airflow',
    git_access_token: localStorage.getItem('repoGitGlobalAccessToken')
  };

  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();

  return $.ajax({
    url: '/api/v1/deploy/data-repo-ci-finaliser',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
    headers: {
      "accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": "Bearer " + window.bearerToken
    }
  }).then(function(response) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;
    
    console.log('API response:', response);
    console.log('Request duration:', duration, 'ms');
    return response;
  }).fail(function(xhr, status, error) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;

    console.error('API error:', error);
    console.log('Request duration:', duration, 'ms');
    throw error;
  });
}

// Load existing values for Tenant Deploy finaliser upload  step
function loadLocalStorageValuesStep10() {
  const cloudProvider = localStorage.getItem('cloudProvider');
  const customerName = localStorage.getItem('customerName');
  const projectId = localStorage.getItem('projectId');
  const ownerEmail = localStorage.getItem('ownerEmail');
  
  console.log(`Loading values for for Git Repo CI values upload step:
    cloudProvider: ${cloudProvider},
    customerName: ${customerName},
    projectId: ${projectId},
    ownerEmail: ${ownerEmail}`);
  
  // Populate the fields in the review section
  $('#reviewTDFCloudProvider').text(cloudProvider || 'N/A');
  $('#reviewTDFProjectID').text(projectId || 'N/A');
  $('#reviewTDFCustomerName').text(customerName || 'N/A');
  $('#reviewTDFownerEmail').text(ownerEmail || 'N/A');
}

// Handle Git Repo finaliser step
function handleTenantDeploymentFinaliserStep() {
  function checkFormValidity() {
    return $('#confirmationTDFCheckbox').is(':checked');
  }

  function updateNextButtonVisibility() {
    if (checkFormValidity()) {
      $('.actions > ul > li:eq(2)').show(); // Show Finish button
      //....
    } else {
      $('.actions > ul > li:eq(1)').hide(); // Hide Next button
    }
  }

  // Initial check
  updateNextButtonVisibility();

  // Add event listener to the confirmation checkbox
  $('#confirmationTDFCheckbox').off('change').on('change', updateNextButtonVisibility);
}

// Function to submit Tenant Deployment finaliser request
function submitTenantDeployFinaliserRequest() {  
  const data = {
    cloud_provider: localStorage.getItem('cloudProvider'),
    customer: localStorage.getItem('customerName'),
    user_email: localStorage.getItem('ownerEmail'),
    git_access_token: localStorage.getItem('repoGitGlobalAccessToken')
  };

  console.log('Sending data to API:', data);

  var startTime = new Date().getTime();

  return $.ajax({
    url: '/api/v1/deploy/deployment-files-save',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
    headers: {
      "accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": "Bearer " + window.bearerToken
    }
  }).then(function(response) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;
    
    console.log('API response:', response);
    console.log('Request duration:', duration, 'ms');
    return response;
  }).fail(function(xhr, status, error) {
    var endTime = new Date().getTime();
    var duration = endTime - startTime;

    console.error('API error:', error);
    console.log('Request duration:', duration, 'ms');
    throw error;
  });
}

// Cloud provider selection
let gcpAuthInProgress = false;

document.getElementById('gcp-block').addEventListener('click', () => {
  if (!gcpAuthInProgress) {
    gcpAuthInProgress = true;
    
    // Open the authentication window
    const authWindow = window.open('/api/v1/login_gcp', 'GCP Auth', 'width=600,height=600');

    // Set up a listener for messages from the popup
    window.addEventListener('message', function(event) {
      // Add origin check if needed
      // if (event.origin !== "http://localhost:8888") return;
      
      if (event.data.status === "success" && event.data.token_key) {
        gcpAuthInProgress = false;
        
        const tokenKeyValue = event.data.token_key;
        console.log('Token Key:', tokenKeyValue);
        document.getElementById('tokenKeyValue').value = tokenKeyValue;
        
        // Optionally, you can display a message to the user
        //alert('Authentication successful!');
      }
    });

    // Set a timeout to reset the auth flag if the process takes too long
    setTimeout(() => {
      if (gcpAuthInProgress) {
        gcpAuthInProgress = false;
        console.log('Authentication timed out');
        // Optionally, display a message to the user
        alert('Authentication timed out. Please try again.');
      }
    }, 5 * 60 * 1000); // 5 minutes timeout
  }
});

let awsWindowOpen = false;
document.getElementById('aws-block').addEventListener('click', () => {
if (!awsWindowOpen) {
    const awsWindow = window.open('/api/v1/login_aws', '_blank');
    awsWindowOpen = true;
    awsWindow.addEventListener('load', () => {
    const tokenKey = awsWindow.document.querySelector('pre').textContent;
    const tokenKeyJson = JSON.parse(tokenKey);
    const tokenKeyValue = tokenKeyJson.token_key;
    // Use the token_key value for subsequent actions
    console.log('Token Key:', tokenKeyValue);
    // You can now use the token_key value to make API calls or perform other actions
    });
}
});

let azureWindowOpen = false;
document.getElementById('azure-block').addEventListener('click', () => {
if (!azureWindowOpen) {
    const azureWindow = window.open('/api/v1/login_azure', '_blank');
    azureWindowOpen = true;
    azureWindow.addEventListener('load', () => {
    const tokenKey = azureWindow.document.querySelector('pre').textContent;
    const tokenKeyJson = JSON.parse(tokenKey);
    const tokenKeyValue = tokenKeyJson.token_key;
    // Use the token_key value for subsequent actions
    console.log('Token Key:', tokenKeyValue);
    // You can now use the token_key value to make API calls or perform other actions
    });
}
});

document.getElementById('on-premise-block').addEventListener('click', () => {
// Handle on-premise selection
console.log('On-premise selected');
});

window.addEventListener('message', (event) => {
    if (event.data.token_key) {
      const tokenKeyValue = event.data.token_key;
      // Update the #tokenKeyValue input field
      document.getElementById('tokenKeyValue').value = tokenKeyValue;
    }
  });

// Get the tokenKeyValue from the previous step
var tokenKeyValue = $('input[name="purpose"]:checked').data('token-key');

// Populate the input field with the tokenKeyValue
$('#tokenKeyValue').val(tokenKeyValue);



// Get the cloud provider radio buttons
const providerRadios = document.querySelectorAll('input[name="purpose"]');

// Add an event listener to each radio button
providerRadios.forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const selectedProvider = e.target.value;
      const formGroups = document.querySelectorAll('.form-group');
  
      // Hide all form groups except non-cloud-dependent fields
      formGroups.forEach((formGroup) => {
        if (formGroup.getAttribute('data-provider') === 'non-cloud-dependent') {
          formGroup.style.display = 'block'; // Always show non-cloud-dependent fields
        } else {
          formGroup.style.display = 'none'; // Hide other fields
        }
      });
  
      // Show only the form groups that belong to the selected provider
      const providerFormGroups = document.querySelectorAll(`.form-group[data-provider="${selectedProvider}"]`);
      providerFormGroups.forEach((formGroup) => {
        formGroup.style.display = 'block';
      });
    });
  });

// Initial load: Ensure non-cloud-dependent fields are visible
document.querySelectorAll('.form-group[data-provider="non-cloud-dependent"]').forEach((formGroup) => {
    formGroup.style.display = 'block';
  });

$(document).ready(function() {
    // Make sure non-cloud-dependent fields are always visible on page load
    $('.form-group[data-provider="non-cloud-dependent"]').show();
  
    // Event listener for provider selection
    $('input[name="purpose"]').on('change', function() {
      const selectedProvider = $(this).val();
  
      // Hide all form groups except non-cloud-dependent
      $('.form-group').hide();
      $('.form-group[data-provider="non-cloud-dependent"]').show();
  
      // Show only the form groups that belong to the selected provider
      $(`.form-group[data-provider="${selectedProvider}"]`).show();
    });
  });
