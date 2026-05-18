# Using the Administrator Dashboard

Once HydroServer is running and accessible, additional configuration settings can be managed through the admin 
dashboard.

1. **Access the Admin Dashboard**  
   Log in at: `https://<your-hydroserver-domain>/admin`

2. **Update the Default Site Domain**  
   - Go to **Sites** > **example.com**  
   - Change the default domain to match your HydroServer domain.  

3. **Configure Website Settings** (under **Web**)  
   - **Instance Configuration**: Customize the `About` page with information about your organization.  
   - **Analytics Configuration**: Optionally enable [Microsoft Clarity](https://clarity.microsoft.com/).  
   - **Map Configuration**: Define default map layers, view, geospatial, and elevation services.  
   - **Map Layers**: Add additional map layer options for pages that use maps.  
   - **Contact Information**: Add organization contact information for display on the `About` page.  

4. **Set Up Identity Providers**  
   - Navigate to **Social Applications** > **Add Social Application**.  
   - Select a supported provider (e.g., Google, HydroShare).  
   - Enter a unique ID, name, client ID/key, and secret key from the provider.  
   - (Optional) Add JSON settings, for example:  
     ```json
     {
       "allowSignUp": true,
       "allowConnection": true
     }
     ```  
     - **allowSignUp**: (true/false) — whether users can sign up and log in with this provider.  
     - **allowConnection**: (true/false) — whether users can connect the provider to an existing HydroServer account.  
   - Assign the default site that the provider can authenticate against.  

5. **Load Default Reference Data**  
   Populate the following models with data available to all users, or use the **Load Default Data** option in each
   model:  
   - Roles  
   - Observed Properties  
   - Processing Levels  
   - Result Qualifiers  
   - Sensors  
   - Units  

6. **Add HydroServer Vocabularies**
   There are several user forms throughout HydroServer that can be populated with custom values. These values can be 
   added through the admin dashboard by populating the following models:
   - **Identity and Access Management** > **User Types**
   - **Identity and Access Management** > **Organization Types**
   - **Measurement Data** > **Datastream Aggregations**
   - **Measurement Data** > **Datastream Statuses**
   - **Measurement Data** > **Method Types**
   - **Measurement Data** > **Sampled Mediums**
   - **Measurement Data** > **Sampling Feature Types**
   - **Measurement Data** > **Sensor Encoding Types**
   - **Measurement Data** > **Site Types**
   - **Measurement Data** > **Unit Types**
   - **Measurement Data** > **Variable Types**

7. **Configure HydroServer ETL** (optional)
   If you have set up a HydroServer Celery scheduler and worker, you must load a default HydroServer orchestration 
   system. To do so, navigate to **Orchestration Systems** and click **Load Internal Orchestration System**.
