// // NOT USED

// // Handle page load/refresh
// $(document).ready(function() {
//   var currentIndex = $('#wizard').steps('getCurrentIndex');
  
//   // Check if we have an existing wizard session
//   if (!localStorage.getItem('wizardSessionStarted')) {
//     // This is a new session, clear any old data
//     localStorage.clear();
//     localStorage.setItem('wizardSessionStarted', 'true');
//     console.log('New wizard session started, localStorage cleared');
//   } else {
//     console.log('Existing wizard session, localStorage preserved');
//   }

//   setupStepVisibility(currentIndex);
// });

// // Add this function to your code
// function resetWizard() {
//   localStorage.removeItem('wizardSessionStarted');
//   localStorage.clear();
//   console.log('Wizard reset, localStorage cleared');
//   // Optionally, redirect to the first step or reload the page
//   // window.location.reload();
// }

// // Wizard Init
// $("#wizard").steps({
//     headerTag: "h3",
//     bodyTag: "section",
//     transitionEffect: "none",
//     stepsOrientation: "vertical",
//     titleTemplate: '<span class="number">#index#</span>'
//   });

// // Cloud provider selection
// $('#gcp-block, #aws-block, #azure-block, #on-premise-block').on('click', function() {
//     var selectedProvider = $(this).attr('data-provider');
//     var selectedProviderDWH = $(this).attr('data-service');
//     localStorage.setItem('cloudProvider', selectedProvider);
//     localStorage.setItem('cloudProviderDWH', selectedProviderDWH);
// });

// // Cloud provider selection
// let gcpWindowOpen = false;
// document.getElementById('gcp-block').addEventListener('click', () => {
//   if (!gcpWindowOpen) {
//     const gcpWindow = window.open('/api/v1/login_gcp', '_blank');
//     gcpWindowOpen = true;

//     window.addEventListener('message', (event) => {
//       if (event.data.token_key) {
//         const tokenKeyValue = event.data.token_key;
//         console.log('Token Key:', tokenKeyValue);
//         // Use the token key value for subsequent actions
//         document.getElementById('tokenKeyValue').value = tokenKeyValue;
//         gcpWindow.close();
//       }
//     });
//   }
// });

// // Define the regular expression pattern
// var whitelistIPPattern = /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2})(, (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}))*$/;

// // Add an event listener to the gcp-whitelistIPs input field
// $('#gcp-whitelistIPs').on('input', function() {
//   var whitelistIPsValue = $(this).val();
//   if (!whitelistIPPattern.test(whitelistIPsValue)) {
//     // If the input doesn't match the pattern, show an error message
//     $(this).addClass('is-invalid');
//     $(this).next('.invalid-feedback').text('Invalid whitelist IP format. Please use the format "IP/CIDR, IP/CIDR, ..."');
//   } else {
//     // If the input matches the pattern, remove the error message
//     $(this).removeClass('is-invalid');
//     $(this).next('.invalid-feedback').text('');
//   }
// });

// $(document).ready(function() {
//     $('#wizard').on('stepChanged', function(event, currentIndex) {
//         // If we're on Step 3 (index 2)
//         if (currentIndex === 2) {
//             // Retrieve the stored values from localStorage
//             const customerName = localStorage.getItem('customerName');
//             const ownerEmail = localStorage.getItem('ownerEmail');
            
//             // Populate the fields in the review section
//             $('#reviewCustomerName').text(customerName || 'N/A');
//             $('#reviewEmail').text(ownerEmail || 'N/A');
//         }
//     });
// });

// // Store Step 2 values when moving to the next step
// $('a[href="#next"]').on('click', function() {
//     if ($('#wizard').steps('getCurrentIndex') === 2) { // Check if we're on Step 2
//       var cloudProvider = localStorage.getItem('cloudProvider');
      
//       // Store values based on the selected cloud provider
//       if (cloudProvider === 'gcp') {
//         localStorage.setItem('tokenKey', $('#tokenKeyValue').val());
//         localStorage.setItem('billingAccountId', $('#gcp-billingAccountID').val());
//         localStorage.setItem('orgFolderId', $('#gcp-orgFolderId').val());
//         localStorage.setItem('customerName', $('#gcp-customerName').val());
//         localStorage.setItem('ownerEmail', $('#gcp-adminEmailAddress').val());
//         localStorage.setItem('region', $('#gcp-region').val());
//         localStorage.setItem('projectId', $('#gcp-projectID').val());
//         localStorage.setItem('whitelistIPs', $('#gcp-whitelistIPs').val());
//       } else if (cloudProvider === 'aws') {
//         localStorage.setItem('billingAccountId', $('#aws-billingAccountID').val());
//         localStorage.setItem('customerName', $('#aws-customerName').val());
//         localStorage.setItem('ownerEmail', $('#aws-adminEmailAddress').val());
//         localStorage.setItem('region', $('#aws-region').val());
//         localStorage.setItem('whitelistIPs', $('#aws-whitelistIPs').val());
//       } else if (cloudProvider === 'azure') {
//         localStorage.setItem('billingAccountId', $('#azure-billingAccountID').val());
//         localStorage.setItem('customerName', $('#azure-customerName').val());
//         localStorage.setItem('ownerEmail', $('#azure-adminEmailAddress').val());
//         localStorage.setItem('region', $('#azure-region').val());
//         localStorage.setItem('whitelistIPs', $('#azure-whitelistIPs').val());
//       } else if (cloudProvider === 'on-premise') {
//         localStorage.setItem('customerName', $('#on-premise-customerName').val());
//         localStorage.setItem('ownerEmail', $('#on-premise-adminEmailAddress').val());
//         localStorage.setItem('kubernetesEndpoint', $('#on-premise-k8s-endpoint').val());
//         localStorage.setItem('whitelistIPs', $('#on-premise-whitelistIPs').val());
//       }

//       // Debug
//       // Show in log is the fields was filled.
//       console.log('Step 2 values stored:', {
//         cloudProvider: cloudProvider,
//         tokenKey: localStorage.getItem('tokenKey'),
//         billingAccountId: localStorage.getItem('billingAccountId'),
//         customerName: localStorage.getItem('customerName'),
//         ownerEmail: localStorage.getItem('ownerEmail'),
//         region: localStorage.getItem('region'),
//         projectId: localStorage.getItem('projectId'),
//         whitelistIPs: localStorage.getItem('whitelistIPs'),
//         kubernetesEndpoint: localStorage.getItem('kubernetesEndpoint')
//       });
//     }
//   });

// // Store Step 3 on "next" values when moving to the next step
// $('a[href="#next"]').on('click', function() {
//     if ($('#wizard').steps('getCurrentIndex') === 3) { // Check if we're on Step 3
//       localStorage.setItem('vaultClientId', $('#vaultClientId').val());
//       localStorage.setItem('vaultClientSecret', $('#vaultClientSecret').val());
//       // Debug
//       // Show in log is the vault client fields was filled.
//       console.log('Step 3 values stored:', {
//         cloudProvider: localStorage.getItem('cloudProvider'),
//         customerName: localStorage.getItem('customerName'),
//         ownerEmail: localStorage.getItem('ownerEmail'),
//         vaultClientId: localStorage.getItem('vaultClientId'),
//         vaultClientSecret: localStorage.getItem('vaultClientSecret')
//       });
//     }
//   });

// // Handle Step 3 form submission (Create customer vault)
// $('a[href="#next"]').on('click', function(e) {
//   if ($('#wizard').steps('getCurrentIndex') === 3) { // Check if we're on Step 3
//       e.preventDefault(); // Prevent default next action

//       // Prepare data for API request
//       var data = {
//           client_id: localStorage.getItem('vaultClientId'),
//           client_secret: localStorage.getItem('vaultClientSecret'),
//           customer: localStorage.getItem('customerName'),
//           user_email: localStorage.getItem('ownerEmail')
//       };
//       console.log('Sending data to API:', data);

//       var startTime = new Date().getTime();

//       // Send synchronous POST request to API
//       $.ajax({
//           url: '/api/v1/create-customer-vault',
//           type: 'POST',
//           contentType: 'application/json',
//           data: JSON.stringify(data),
//           headers: {
//               "accept": "application/json",
//               "Content-Type": "application/json",
//               "Authorization": "Bearer sB4J1EZpeGtZ9IbOZn6VZY50oM2Y2jr3sHdMpT"
//           },
//           async: false, // Make the request synchronous
//           success: function(response) {
//               var endTime = new Date().getTime();
//               var duration = endTime - startTime;
              
//               console.log('API response:', response);
//               console.log('Request duration:', duration, 'ms');

//               // If successful, move to the next step
//               // $('#wizard').steps('next');
//               //$('#wizard').steps('goto', 4);
//           },
//           error: function(xhr, status, error) {
//               var endTime = new Date().getTime();
//               var duration = endTime - startTime;

//               console.error('API error:', error);
//               console.log('Request duration:', duration, 'ms');

//               // Show error message only for actual errors
//               alert('Error: ' + error);
//           }
//       });
//   }
// });

// // Store Step 4 on "next" values when moving to the next step
// $(document).ready(function() {
//   $('#wizard').on('stepChanged', function(event, currentIndex) {
//       // If we're on Step 4 (index 3)
//       if (currentIndex === 3) {
//           // Retrieve the stored values from localStorage
//           const tokenKey = localStorage.getItem('tokenKey');
//           const cloudProvider = localStorage.getItem('cloudProvider');
//           const billingAccountId = localStorage.getItem('billingAccountId');
//           const orgFolderId = localStorage.getItem('orgFolderId');
//           const customerName = localStorage.getItem('customerName');
//           const ownerEmail = localStorage.getItem('ownerEmail');
//           const region = localStorage.getItem('region');
//           const projectId = localStorage.getItem('projectId');
//           const whitelistIPs = localStorage.getItem('whitelistIPs');
  
//           // Populate the fields in the review section
//           $('#reviewTFCloudProvider').text(cloudProvider || 'N/A');
//           $('#reviewTFTokenKey').text(tokenKey || 'N/A');
//           $('#reviewTFBillingAccount').text(billingAccountId || 'N/A');
//           $('#reviewTForgFolderId').text(orgFolderId || 'N/A');
//           $('#reviewTFRegion').text(region || 'N/A');
//           $('#reviewProjectID').text(projectId || 'N/A');
//           $('#reviewTFCustomerName').text(customerName || 'N/A');
//           $('#reviewTFEmail').text(ownerEmail || 'N/A');
//           $('#reviewTFWhitelistIPs').text(whitelistIPs || 'N/A');
//       }
//   });
// });

// // Store Step 4 on "next" values when moving to the next step
// $('a[href="#next"]').on('click', function() {
//   if ($('#wizard').steps('getCurrentIndex') === 4) { // Check if we're on Step 4
//     localStorage.setItem('deploymentType', $('#deploymentType').val());
//     // Debug
//     // Show in log is the vault client fields was filled.
//     console.log('Step 4 values stored:', {
//       deploymentType: localStorage.getItem('deploymentType'),
//       tokenKey: localStorage.getItem('tokenKey'),
//       cloudProvider: localStorage.getItem('cloudProvider'),
//       billingAccountId: localStorage.getItem('billingAccountId'),
//       orgFolderId: localStorage.getItem('orgFolderId'),
//       customerName: localStorage.getItem('customerName'),
//       ownerEmail: localStorage.getItem('ownerEmail'),
//       region: localStorage.getItem('region'),
//       projectId: localStorage.getItem('projectId'),
//       whitelistIPs: localStorage.getItem('whitelistIPs')
//     });
//   }
// });

// // Handle Step 4 form submission (Create customer vault)
// $('a[href="#next"]').on('click', function(e) {
//   if ($('#wizard').steps('getCurrentIndex') === 4) { // Check if we're on Step 4
//       e.preventDefault(); // Prevent default next action
//       // Prepare data for API request
//       var data = {
//           cloud_provider: localStorage.getItem('cloudProvider'),
//           deployment: localStorage.getItem('deploymentType'),
//           billing_account_id: localStorage.getItem('billingAccountId'),
//           parent_folder: localStorage.getItem('orgFolderId'),
//           customer: localStorage.getItem('customerName'),
//           user_email: localStorage.getItem('ownerEmail'),
//           region: localStorage.getItem('region'),
//           project_id: localStorage.getItem('projectId'),
//           whitelist_ips: localStorage.getItem('whitelistIPs')
//       };
//       console.log('Sending data to API:', data);

//       var startTime = new Date().getTime();

//       // Send synchronous POST request to API
//       $.ajax({
//           url: '/api/v1/deploy/infra-environment',
//           type: 'POST',
//           contentType: 'application/json',
//           data: JSON.stringify(data),
//           headers: {
//               "accept": "application/json",
//               "Content-Type": "application/json",
//               "Authorization": "Bearer sB4J1EZpeGtZ9IbOZn6VZY50oM2Y2jr3sHdMpT"
//           },
//           async: false, // Make the request synchronous
//           success: function(response) {
//               var endTime = new Date().getTime();
//               var duration = endTime - startTime;
              
//               console.log('API response:', response);
//               console.log('Request duration:', duration, 'ms');

//               // If successful, move to the next step
//               // $('#wizard').steps('next');
//               //$('#wizard').steps('goto', 4);
//           },
//           error: function(xhr, status, error) {
//               var endTime = new Date().getTime();
//               var duration = endTime - startTime;

//               console.error('API error:', error);
//               console.log('Request duration:', duration, 'ms');

//               // Show error message only for actual errors
//               alert('Error: ' + error);
//           }
//       });
//   }
// });