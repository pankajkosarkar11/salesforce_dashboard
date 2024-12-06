import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # Import for Scattergeo
from simple_salesforce import Salesforce, SalesforceLogin
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import logging

# ---------------------------
# Configuration and Setup
# ---------------------------

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit app configuration
st.set_page_config(page_title="Salesforce Lead Dashboard", layout="wide")

# Apply custom CSS for smaller table font, aligned legend, and table headers
st.markdown(
    """
    <style>
    /* Reduce sidebar width */
    [data-testid="stSidebar"][aria-expanded="true"] {
        width: 250px;
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 250px;
        /* Allow main content to expand by not setting a negative margin */
        /* margin-left: -250px; */ /* Removed to prevent white padding */
    }

    /* Smaller table font */
    .dataframe {
        font-size: 12px !important;
    }

    /* Aligned legend font size */
    .plotly-legend {
        font-size: 10px !important;
    }

    /* Table header styling */
    .table-header {
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 8px;
    }

    /* AgGrid header row background */
    .ag-header-row {
        background-color: #8aba7d !important;
    }

    /* Custom scrollbar for AgGrid */
    .ag-body-viewport {
        overflow: auto !important;
    }

    /* Adjust main content padding to eliminate white space */
    [data-testid="stAppViewContainer"] > .main {
        padding-right: 1rem;
        padding-left: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Helper Data and Mappings
# ---------------------------

# Allowed Lead Sources
ALLOWED_LEAD_SOURCES = [
    "Indeed",
    "Google Leads - Website",
    "Website",
    "Customer Referral",
    "Self Generated"
]

# Define state centroids (latitude and longitude)
STATE_CENTROIDS = {
    'AL': {'lat': 32.806671, 'lon': -86.791130},
    'AK': {'lat': 61.370716, 'lon': -152.404419},
    'AZ': {'lat': 33.729759, 'lon': -111.431221},
    'AR': {'lat': 34.969704, 'lon': -92.373123},
    'CA': {'lat': 36.116203, 'lon': -119.681564},
    'CO': {'lat': 39.059811, 'lon': -105.311104},
    'CT': {'lat': 41.597782, 'lon': -72.755371},
    'DE': {'lat': 39.318523, 'lon': -75.507141},
    'FL': {'lat': 27.766279, 'lon': -81.686783},
    'GA': {'lat': 33.040619, 'lon': -83.643074},
    'HI': {'lat': 21.094318, 'lon': -157.498337},
    'ID': {'lat': 44.240459, 'lon': -114.478828},
    'IL': {'lat': 40.349457, 'lon': -88.986137},
    'IN': {'lat': 39.849426, 'lon': -86.258278},
    'IA': {'lat': 42.011539, 'lon': -93.210526},
    'KS': {'lat': 38.526600, 'lon': -96.726486},
    'KY': {'lat': 37.668140, 'lon': -84.670067},
    'LA': {'lat': 31.169546, 'lon': -91.867805},
    'ME': {'lat': 44.693947, 'lon': -69.381927},
    'MD': {'lat': 39.063946, 'lon': -76.802101},
    'MA': {'lat': 42.230171, 'lon': -71.530106},
    'MI': {'lat': 43.326618, 'lon': -84.536095},
    'MN': {'lat': 45.694454, 'lon': -93.900192},
    'MS': {'lat': 32.741646, 'lon': -89.678696},
    'MO': {'lat': 38.456085, 'lon': -92.288368},
    'MT': {'lat': 46.921925, 'lon': -110.454353},
    'NE': {'lat': 41.125370, 'lon': -98.268082},
    'NV': {'lat': 38.313515, 'lon': -117.055374},
    'NH': {'lat': 43.452492, 'lon': -71.563896},
    'NJ': {'lat': 40.298904, 'lon': -74.521011},
    'NM': {'lat': 34.840515, 'lon': -106.248482},
    'NY': {'lat': 42.165726, 'lon': -74.948051},
    'NC': {'lat': 35.630066, 'lon': -79.806419},
    'ND': {'lat': 47.528912, 'lon': -99.784012},
    'OH': {'lat': 40.388783, 'lon': -82.764915},
    'OK': {'lat': 35.565342, 'lon': -96.928917},
    'OR': {'lat': 44.572021, 'lon': -122.070938},
    'PA': {'lat': 40.590752, 'lon': -77.209755},
    'RI': {'lat': 41.680893, 'lon': -71.511780},
    'SC': {'lat': 33.856892, 'lon': -80.945007},
    'SD': {'lat': 44.299782, 'lon': -99.438828},
    'TN': {'lat': 35.747845, 'lon': -86.692345},
    'TX': {'lat': 31.054487, 'lon': -97.563461},
    'UT': {'lat': 40.150032, 'lon': -111.862434},
    'VT': {'lat': 44.045876, 'lon': -72.710686},
    'VA': {'lat': 37.769337, 'lon': -78.169968},
    'WA': {'lat': 47.400902, 'lon': -121.490494},
    'WV': {'lat': 38.491226, 'lon': -80.954453},
    'WI': {'lat': 44.268543, 'lon': -89.616508},
    'WY': {'lat': 42.755966, 'lon': -107.302490}
}

FULL_STATE_NAMES = set([
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "Washington D.C."
])

STATE_ABBREVIATIONS = set(STATE_CENTROIDS.keys())

# Mapping of state abbreviations to full state names
STATE_ABBR_TO_NAME = {
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VT': 'Vermont',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming',
    'DC': 'Washington D.C.'
}

# ---------------------------
# Helper Functions
# ---------------------------

def remap_lead_source(lead_sources):
    """
    Remap LeadSource values to allowed values or 'Other'.
    """
    return lead_sources.apply(lambda x: x if x in ALLOWED_LEAD_SOURCES else "Other")

def determine_state(row):
    """
    Determines the state abbreviation of a lead from the State, Lead_State_Province__c, and Street fields.
    Returns the two-letter state abbreviation if found, else None.
    """
    for field in ['State', 'Lead_State_Province__c', 'Street']:
        value = row.get(field, "")
        if isinstance(value, str):
            value = value.strip()
            if value.upper() in STATE_ABBREVIATIONS:
                return value.upper()
            elif value.title() in FULL_STATE_NAMES:
                # Find the abbreviation based on full state name
                for abbr, name in STATE_ABBR_TO_NAME.items():
                    if name == value.title():
                        return abbr
    return None

def handle_login(username, password, security_token, domain):
    """
    Authenticate with Salesforce and update session state.
    """
    try:
        logger.info("Attempting to authenticate with Salesforce.")
        session_id, instance = SalesforceLogin(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain
        )
        st.session_state.sf = Salesforce(instance=instance, session_id=session_id)
        st.session_state.logged_in = True
        st.session_state.login_message = "Logged in to Salesforce successfully!"
        st.session_state.login_success = True
        logger.info("Salesforce authentication successful.")
    except SalesforceAuthenticationFailed:
        logger.error("Salesforce authentication failed.")
        st.session_state.logged_in = False
        st.session_state.login_message = "Authentication failed. Please check your credentials."
        st.session_state.login_success = False
    except Exception as e:
        logger.exception("An unexpected error occurred during login.")
        st.session_state.logged_in = False
        st.session_state.login_message = f"An error occurred: {e}"
        st.session_state.login_success = False

def calculate_table_height(row_count, row_height=30, min_height=200, max_height=600):
    """
    Calculate the height of the table dynamically based on the number of rows.
    """
    total_height = row_count * row_height
    return max(min(total_height, max_height), min_height)

# ---------------------------
# Authentication Section
# ---------------------------

def authentication_section(login_placeholder):
    """
    Renders the login interface and handles Salesforce authentication.
    Only displays the form if the user is not logged in.
    """
    with login_placeholder.container():
        if not st.session_state.get('logged_in', False):
            st.title("Salesforce Lead Analysis")
            st.subheader("Login to Salesforce")
            username = st.text_input("Salesforce Username")
            password = st.text_input("Salesforce Password", type="password")
            security_token = st.text_input("Salesforce Security Token", type="password")
            domain = st.selectbox("Salesforce Domain", ["login", "test"])

            if st.button("Login"):
                if username and password and security_token:
                    handle_login(username, password, security_token, domain)
                else:
                    st.warning("Please provide all required credentials.")

            # Display login message if any
            if 'login_message' in st.session_state and st.session_state.login_message:
                if st.session_state.get('login_success', False):
                    st.success(st.session_state.login_message)
                else:
                    st.error(st.session_state.login_message)
                # Reset the message after displaying
                st.session_state.login_message = ""
                st.session_state.login_success = False
        else:
            # User is logged in; do not display the login form
            pass

# ---------------------------
# Data Fetching and Processing Section
# ---------------------------

def fetch_and_process_lead_data():
    """
    Fetches lead data from Salesforce and processes it.
    """
    if st.session_state.lead_data is None:
        try:
            logger.info("Fetching lead data from Salesforce.")
            soql_query = """
            SELECT Id, Status, CreatedDate, OwnerId, LeadSource, Owner.Name, junk__c, Name,
            Email, MobilePhone, Product__c, Company, State, Lead_State_Province__c, Street
            FROM Lead
            """
            lead_records = st.session_state.sf.query_all(soql_query)

            if lead_records['totalSize'] > 0:
                df_leads = pd.json_normalize(lead_records['records'])

                if 'attributes' in df_leads.columns:
                    df_leads.drop(columns='attributes', inplace=True)

                df_leads['CreatedDate'] = pd.to_datetime(df_leads['CreatedDate'])
                df_leads.rename(columns={'Owner.Name': 'OwnerName'}, inplace=True)
                df_leads['LeadSource'] = remap_lead_source(df_leads['LeadSource'])

                # Determine state for each lead
                df_leads['LeadState'] = df_leads.apply(determine_state, axis=1)
                df_leads = df_leads.dropna(subset=['LeadState'])  # Drop leads where state couldn't be determined

                st.session_state.lead_data = df_leads
                logger.info(f"Fetched {len(df_leads)} lead records.")
            else:
                st.warning("No lead records found.")
                logger.warning("No lead records found in Salesforce.")
        except Exception as e:
            logger.exception("An error occurred while fetching lead data.")
            st.error(f"An error occurred while fetching lead data: {e}")

# ---------------------------
# Filtering Section
# ---------------------------

def filtering_section(df_leads):
    """
    Renders filter widgets in the sidebar and applies selected filters to the lead data.

    Returns:
        pd.DataFrame: Filtered DataFrame.
        bool: Show Lead Analysis Charts
        bool: Show Monthly Lead Distribution
        bool: Show US Map
    """
    # Begin sidebar section
    st.sidebar.markdown("### Filters")

    # Year selection multiselect with 'All' logic
    years = df_leads['CreatedDate'].dt.year.unique()
    years.sort()
    years = ['All'] + list(years.astype(str))

    # Initialize session state for year_selection
    if 'year_selection' not in st.session_state:
        st.session_state.year_selection = ['All']

    def update_year():
        selected = st.session_state.year_selection
        if 'All' in selected:
            if len(selected) > 1:
                # Remove 'All' if other years are selected
                st.session_state.year_selection = [year for year in selected if year != 'All']
        elif not selected:
            # If no selection, reset to 'All'
            st.session_state.year_selection = ['All']

    selected_year = st.sidebar.multiselect(
        "Select Year",
        options=years,
        default=st.session_state.year_selection,
        key='year_selection',
        on_change=update_year
    )

    # Owner Name selection multiselect with 'All' logic
    owner_names = df_leads['OwnerName'].dropna().unique()
    owner_names.sort()
    owner_names = ['All'] + list(owner_names)

    # Initialize session state for owner_selection
    if 'owner_selection' not in st.session_state:
        st.session_state.owner_selection = ['All']

    def update_owner():
        selected = st.session_state.owner_selection
        if 'All' in selected:
            if len(selected) > 1:
                # Remove 'All' if other owners are selected
                st.session_state.owner_selection = [owner for owner in selected if owner != 'All']
        elif not selected:
            # If no selection, reset to 'All'
            st.session_state.owner_selection = ['All']

    selected_owner = st.sidebar.multiselect(
        "Select Owner",
        options=owner_names,
        default=st.session_state.owner_selection,
        key='owner_selection',
        on_change=update_owner
    )

    # Lead Source selection multiselect with 'All' logic
    lead_sources = df_leads['LeadSource'].dropna().unique()
    custom_order = [
        "Google Leads - Website",
        "Website",
        "Customer Referral",
        "Self Generated",
        "Indeed",
        "Other"
    ]
    lead_sources = sorted(lead_sources, key=lambda x: custom_order.index(x) if x in custom_order else len(custom_order))
    lead_sources = ['All'] + list(lead_sources)

    # Initialize session state for lead_source_selection
    if 'lead_source_selection' not in st.session_state:
        st.session_state.lead_source_selection = ['All']

    def update_lead_source():
        selected = st.session_state.lead_source_selection
        if 'All' in selected:
            if len(selected) > 1:
                # Remove 'All' if other lead sources are selected
                st.session_state.lead_source_selection = [source for source in selected if source != 'All']
        elif not selected:
            # If no selection, reset to 'All'
            st.session_state.lead_source_selection = ['All']

    selected_lead_source = st.sidebar.multiselect(
        "Select Lead Source",
        options=lead_sources,
        default=st.session_state.lead_source_selection,
        key='lead_source_selection',
        on_change=update_lead_source
    )

    # Lead Status selection multiselect with enhanced behavior
    lead_status = df_leads['Status'].dropna().unique()
    lead_status = sorted(lead_status)

    # Initialize session state for lead_status_selection
    if 'lead_status_selection' not in st.session_state:
        st.session_state.lead_status_selection = ['All']

    def update_lead_status():
        selected = st.session_state.lead_status_selection
        if 'All' in selected:
            if len(selected) > 1:
                # Remove 'All' if other statuses are selected
                st.session_state.lead_status_selection = [status for status in selected if status != 'All']
        elif not selected:
            # If no selection, reset to 'All'
            st.session_state.lead_status_selection = ['All']

    selected_lead_status = st.sidebar.multiselect(
        "Select Lead Status",
        options=["All"] + list(lead_status),
        default=st.session_state.lead_status_selection,
        key='lead_status_selection',
        on_change=update_lead_status
    )

    # Product selection multiselect with 'All' logic
    products = df_leads['Product__c'].dropna().unique()
    products = sorted(list(set(products)))
    products = ['All'] + products

    # Initialize session state for product_selection
    if 'product_selection' not in st.session_state:
        st.session_state.product_selection = ['All']

    def update_product():
        selected = st.session_state.product_selection
        if 'All' in selected:
            if len(selected) > 1:
                # Remove 'All' if other products are selected
                st.session_state.product_selection = [product for product in selected if product != 'All']
        elif not selected:
            # If no selection, reset to 'All'
            st.session_state.product_selection = ['All']

    selected_product = st.sidebar.multiselect(
        "Select Product",
        options=products,
        default=st.session_state.product_selection,
        key='product_selection',
        on_change=update_product
    )

    # Date Range Filters
    st.sidebar.markdown("### Date Range Filter")
    date_from = st.sidebar.date_input(
        "From Date",
        value=df_leads['CreatedDate'].min().date(),
        min_value=df_leads['CreatedDate'].min().date(),
        max_value=df_leads['CreatedDate'].max().date()
    )

    date_to = st.sidebar.date_input(
        "To Date",
        value=df_leads['CreatedDate'].max().date(),
        min_value=df_leads['CreatedDate'].min().date(),
        max_value=df_leads['CreatedDate'].max().date()
    )

    # Validate Date Range
    if date_from > date_to:
        st.sidebar.error("**Error:** 'From Date' must be earlier than or equal to 'To Date'. Please adjust the dates.")

    # Add chart selection checkboxes
    st.sidebar.markdown("### Display Options")
    show_lead_analysis = st.sidebar.checkbox("Show Lead Analysis Charts", value=True)
    show_monthly_distribution = st.sidebar.checkbox("Show Monthly Lead Distribution", value=True)
    show_us_map = st.sidebar.checkbox("Show US Map", value=True)

    # Apply filters
    df_filtered = df_leads.copy()

    # Year Filter
    if 'All' not in st.session_state.year_selection:
        try:
            selected_years = [int(year) for year in st.session_state.year_selection]
            df_filtered = df_filtered[df_filtered['CreatedDate'].dt.year.isin(selected_years)]
        except ValueError:
            st.sidebar.error("Invalid year selection.")

    # Owner Filter
    if 'All' not in st.session_state.owner_selection:
        df_filtered = df_filtered[df_filtered['OwnerName'].isin(st.session_state.owner_selection)]

    # Lead Source Filter
    if 'All' not in st.session_state.lead_source_selection:
        df_filtered = df_filtered[df_filtered['LeadSource'].isin(st.session_state.lead_source_selection)]

    # Lead Status Filter
    if 'All' not in st.session_state.lead_status_selection:
        df_filtered = df_filtered[df_filtered['Status'].isin(st.session_state.lead_status_selection)]

    # Product Filter
    if 'All' not in st.session_state.product_selection:
        df_filtered = df_filtered[df_filtered['Product__c'].isin(st.session_state.product_selection)]

    # Apply Date Range Filter only if dates are valid
    if date_from <= date_to:
        df_filtered = df_filtered[
            (df_filtered['CreatedDate'].dt.date >= date_from) &
            (df_filtered['CreatedDate'].dt.date <= date_to)
        ]

    st.sidebar.write(f"**Total Leads:** {df_filtered.shape[0]}")

    return df_filtered, show_lead_analysis, show_monthly_distribution, show_us_map

# ---------------------------
# Visualization Sections
# ---------------------------

def lead_analysis_charts(df_filtered):
    """
    Displays Lead Status and Lead Source pie charts with corresponding tables.
    """
    if not df_filtered.empty:
        st.markdown("### Lead Analysis")
        col1, col2 = st.columns(2, gap="large")

        # Lead Status Analysis
        with col1:
            st.subheader("Lead Status Analysis")
            status_counts = df_filtered['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.pie(
                status_counts,
                names='Status',
                values='Count',
                height=450,
                color_discrete_sequence=px.colors.sequential.Viridis
            )
            fig_status.update_layout(
                legend=dict(orientation="h", y=-0.3),
                margin=dict(t=40, b=40, l=10, r=10)
            )
            st.plotly_chart(fig_status, use_container_width=True)

            # Display the table below the chart
            st.table(status_counts)

        # Lead Source Analysis
        with col2:
            st.subheader("Lead Source Analysis")
            lead_source_counts = df_filtered['LeadSource'].value_counts().reset_index()
            lead_source_counts.columns = ['LeadSource', 'Count']
            fig_source = px.pie(
                lead_source_counts,
                names='LeadSource',
                values='Count',
                height=450,
                color_discrete_sequence=px.colors.sequential.Viridis
            )
            fig_source.update_layout(
                legend=dict(orientation="h", y=-0.3),
                margin=dict(t=40, b=40, l=10, r=10)
            )
            st.plotly_chart(fig_source, use_container_width=True)

            # Display the table below the chart
            st.table(lead_source_counts)
    else:
        st.info("No lead records found for the selected filters.")

def monthly_lead_distribution_chart(df_filtered):
    """
    Displays a stacked horizontal bar chart of monthly lead distribution by status.
    """
    if not df_filtered.empty:
        st.markdown("---")  # Divider
        st.markdown("### Monthly Lead Distribution by Status")
        
        # Create a new DataFrame for monthly aggregation
        df_filtered['Month'] = df_filtered['CreatedDate'].dt.month_name()
        df_filtered['Month_Number'] = df_filtered['CreatedDate'].dt.month
        df_monthly = df_filtered.groupby(['Month', 'Status']).size().reset_index(name='Count')

        # Calculate total leads per month
        df_month_totals = df_monthly.groupby('Month')['Count'].sum().reset_index(name='Total')
        df_monthly = df_monthly.merge(df_month_totals, on='Month')

        # Sort the month names in the correct order (Jan-Dec)
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        df_monthly['Month'] = pd.Categorical(df_monthly['Month'], categories=month_order, ordered=True)
        df_monthly = df_monthly.sort_values(['Month'])

        # Create a stacked bar chart using Plotly
        fig_stacked = px.bar(
            df_monthly,
            y='Month',
            x='Count',
            color='Status',
            orientation='h',
            labels={'Count': 'Number of Leads', 'Month': 'Month', 'Status': 'Lead Status'},
            color_discrete_sequence=px.colors.sequential.Viridis
        )

        # Add total count annotations at the end of each bar
        for i, row in df_month_totals.iterrows():
            fig_stacked.add_annotation(
                x=row['Total'],
                y=row['Month'],
                text=f"<b>{int(row['Total'])}</b>",
                showarrow=False,
                font=dict(size=12, color='black'),
                xanchor="left",
                yanchor="middle"
            )

        # Update the layout
        fig_stacked.update_layout(
            height=700,
            barmode='stack',
            bargap=0.3,
            bargroupgap=0.2,
            margin=dict(t=40, b=40, l=100, r=40)
        )

        st.plotly_chart(fig_stacked, use_container_width=True)
    else:
        st.info("No data available for the selected filters to generate the stacked bar chart.")

def us_map_visualization(df_filtered):
    """
    Creates a US map visualization showing the total count of leads per state.
    On hover, displays total leads and lead counts by sources.
    Adjusts the color bar to be adjacent to the map.
    """
    # Define the specific lead sources
    SPECIFIC_LEAD_SOURCES = [
        "Google Leads - Website",
        "Website",
        "Indeed",
        "Other"  # Assuming 'Other' includes all remaining sources
    ]
    
    # Aggregate total leads per state
    lead_counts_total = df_filtered.groupby('LeadState').size().reset_index(name='Total')
    
    # Aggregate leads per state per lead source
    lead_counts_sources = df_filtered.groupby(['LeadState', 'LeadSource']).size().reset_index(name='Count')
    lead_counts_sources = lead_counts_sources[lead_counts_sources['LeadSource'].isin(SPECIFIC_LEAD_SOURCES)]
    
    # Pivot the data to have lead sources as columns
    lead_pivot = lead_counts_sources.pivot(index='LeadState', columns='LeadSource', values='Count').fillna(0).reset_index()
    
    # Ensure all specific lead sources are present
    for source in SPECIFIC_LEAD_SOURCES:
        if source not in lead_pivot.columns:
            lead_pivot[source] = 0
    
    # Merge total leads
    lead_pivot = lead_pivot.merge(lead_counts_total, on='LeadState', how='left')
    
    # Map state abbreviations to full state names
    lead_pivot['State Name'] = lead_pivot['LeadState'].map(STATE_ABBR_TO_NAME)
    
    # Drop any rows where state name couldn't be determined
    lead_pivot = lead_pivot.dropna(subset=['State Name'])
    
    # Merge with STATE_CENTROIDS to get lat and lon
    lead_pivot = lead_pivot.merge(
        pd.DataFrame.from_dict(STATE_CENTROIDS, orient='index').reset_index().rename(columns={'index': 'State Code'}),
        left_on='LeadState',
        right_on='State Code',
        how='left'
    )
    
    # Create the choropleth for total leads
    fig = px.choropleth(
        lead_pivot,
        locations='State Code',
        locationmode="USA-states",
        color='Total',
        scope="usa",
        color_continuous_scale="Viridis",
        labels={'Total': 'Number of Leads'},
        hover_data={
            'State Code': False,
            'Total': False  # We'll handle hovertext separately
        },
    )
    
    # Customize hover template to include breakdown by sources
    hover_texts = []
    for _, row in lead_pivot.iterrows():
        hover_text = (
            f"State: {row['State Name']}<br>"
            f"Total Leads: {int(row['Total'])}<br>"
        )
        for source in SPECIFIC_LEAD_SOURCES:
            hover_text += f"{source}: {int(row[source])}<br>"
        hover_texts.append(hover_text)
    
    # Add annotations for total leads using Scattergeo
    fig.add_trace(
        go.Scattergeo(
            lon=lead_pivot['lon'],
            lat=lead_pivot['lat'],
            text=lead_pivot['Total'].astype(int),
            mode='text',
            textfont=dict(
                size=10,
                color='white'
            ),
            showlegend=False,
            hoverinfo='none'  # Disable default hover
        )
    )
    
    # Assign the customized hover texts to choropleth
    fig.update_traces(
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    )
    
    # Update the layout to adjust color bar position
    fig.update_layout(
        title_text='Number of Leads per State',
        geo=dict(
            lakecolor='rgb(255, 255, 255)',
            bgcolor='rgba(0,0,0,0)',  # Transparent background
            showlakes=True,
            showsubunits=True,
            subunitcolor="white",
            countrycolor="white",
            showcoastlines=False
        ),
        margin=dict(t=50, b=0, l=0, r=0),
        coloraxis_colorbar=dict(
            title="Number of Leads",
            lenmode="fraction",
            len=0.75,  # Shorter length to make map bigger
            yanchor="middle",
            y=0.5,
            x=1.02,  # Position color bar to the right of the map
            xanchor="left"
        )
    )
    
    # Adjust the figure size
    fig.update_layout(
        autosize=True,  # Allow automatic sizing
        height=700   # Adjusted height
    )
    
    # Create columns for map and ledger with minimal gap
    map_col, ledger_col = st.columns([6, 2], gap="small")
    
    with map_col:
        st.plotly_chart(fig, use_container_width=True)
    
    with ledger_col:
        st.markdown("### Lead Counts per State")
        # Prepare ledger dataframe
        ledger_df = lead_pivot[['LeadState'] + SPECIFIC_LEAD_SOURCES + ['Total']].copy()
        ledger_df = ledger_df.rename(columns={'LeadState': 'State', 'Total': 'Total Leads'})
        
        # Rearrange columns
        ledger_df = ledger_df[['State'] + SPECIFIC_LEAD_SOURCES + ['Total Leads']]
        
        # Initialize AgGrid options
        gb = GridOptionsBuilder.from_dataframe(ledger_df)
        gb.configure_default_column(
            sortable=False,  # Disable sorting
            filter=False,    # Disable filtering
            resizable=True,
            wrapText=True,
            autoHeight=True
        )
        gb.configure_grid_options(domLayout='auto')

        # Configure 'State' column to have decreased width
        gb.configure_column("State", flex=2, min_width=80)
        for source in SPECIFIC_LEAD_SOURCES:
            gb.configure_column(source, flex=1, min_width=60)
        gb.configure_column("Total Leads", flex=1, min_width=60)
        
        grid_options = gb.build()
        
        # Display the ledger as an interactive table with a scrollbar
        AgGrid(
            ledger_df,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            allow_unsafe_jscode=True,
            height=700,  # Set a fixed height with scrollbar
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            theme='streamlit',
            enable_pagination=False,  # Disable pagination
            # Additional parameters can be added if needed
        )

def filtered_records_table(df_filtered):
    """
    Displays filtered lead records in an interactive AgGrid table with custom styling.
    """
    st.markdown("---")
    st.markdown("### Filtered Records")
    
    if df_filtered is not None and not df_filtered.empty:
        # Add a 'Lead Name' column if relevant columns exist
        if 'FirstName' in df_filtered.columns and 'LastName' in df_filtered.columns:
            df_filtered['Lead Name'] = df_filtered['FirstName'].fillna('') + ' ' + df_filtered['LastName'].fillna('')
    
        # Format 'CreatedDate' column for display
        if 'CreatedDate' in df_filtered.columns:
            df_filtered['CreatedDate'] = pd.to_datetime(df_filtered['CreatedDate']).dt.strftime('%d-%b-%Y')
    
        # Define display columns
        display_columns = ['Id', 'Name', 'Product__c', 'OwnerName', 'Status', 'LeadSource', 'CreatedDate']
    
        # Add clickable Salesforce link to the 'Id' column
        salesforce_base_url = st.session_state.sf.base_url.split("/services")[0]
        df_filtered['Id'] = df_filtered['Id'].apply(
            lambda x: f'[Link]({salesforce_base_url}/lightning/r/Lead/{x}/view)'
        )
    
        # Select columns to display
        df_display = df_filtered[display_columns].copy()
    
        # Initialize AgGrid options
        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_default_column(
            sortable=True, filter=True, resizable=True, wrapText=True, autoHeight=True
        )
        gb.configure_pagination(paginationAutoPageSize=False)
        gb.configure_pagination(paginationPageSize=10)  # Set default page size to 10
        grid_options = gb.build()
    
        # Custom CSS for impressive headers
        custom_css = {
            # Header Row Background
            ".ag-header-row": {
                "background-color": "#8aba7d !important",
                "height": "50px !important",
            },
            # Header Cell Styling
            ".ag-header-cell": {
                "font-size": "16px !important",
                "font-family": "Arial, sans-serif !important",
                "color": "white !important",
                "font-weight": "bold !important",
                "text-align": "center !important",
                "display": "flex !important",
                "align-items": "center !important",
                "justify-content": "center !important",
            },
            # Filter Icon Styling
            ".ag-header-icon": {
                "color": "#FFD700 !important",
                "font-size": "16px !important",
                "opacity": "1 !important",
            },
            # Hover Effect for Rows
            ".ag-row-hover": {
                "background-color": "#e0f7ff !important",
            },
        }
    
        # Calculate dynamic height
        row_count = len(df_display)
        table_height = calculate_table_height(row_count)
    
        # Display the AgGrid table
        AgGrid(
            df_display,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            allow_unsafe_jscode=True,
            height=table_height,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            theme='streamlit',
            custom_css=custom_css,
        )
    else:
        st.info("No records found for the selected filters.")

# ---------------------------
# Main Application Flow
# ---------------------------

def main():
    """
    Main function to run the Streamlit app.
    """
    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'sf' not in st.session_state:
        st.session_state.sf = None
    if 'lead_data' not in st.session_state:
        st.session_state.lead_data = None
    if 'login_message' not in st.session_state:
        st.session_state.login_message = ""
    if 'login_success' not in st.session_state:
        st.session_state.login_success = False
    if 'lead_status_selection' not in st.session_state:
        st.session_state.lead_status_selection = ['All']
    if 'year_selection' not in st.session_state:
        st.session_state.year_selection = ['All']
    if 'owner_selection' not in st.session_state:
        st.session_state.owner_selection = ['All']
    if 'lead_source_selection' not in st.session_state:
        st.session_state.lead_source_selection = ['All']
    if 'product_selection' not in st.session_state:
        st.session_state.product_selection = ['All']

    # Create placeholders for login and dashboard
    login_placeholder = st.empty()
    dashboard_placeholder = st.empty()

    # Authentication Section
    authentication_section(login_placeholder)

    # Conditional Rendering: Dashboard only if logged in
    if st.session_state.get('logged_in', False):
        # Render the dashboard in the dashboard_placeholder
        with dashboard_placeholder.container():
            # Display success or error message once after login
            if 'login_message' in st.session_state and st.session_state.login_message:
                if st.session_state.get('login_success', False):
                    st.balloons()  # Optional: Add a celebratory animation
                    st.success(st.session_state.login_message)
                else:
                    st.error(st.session_state.login_message)
                # Reset login_message and login_success to prevent repeated messages
                st.session_state.login_message = ""
                st.session_state.login_success = False

            # Show a loading spinner while fetching data
            if st.session_state.lead_data is None:
                with st.spinner("Loading data..."):
                    fetch_and_process_lead_data()
            
            # Check if lead data was fetched successfully
            if st.session_state.lead_data is not None and not st.session_state.lead_data.empty:
                st.success("Data loaded successfully!")

                # Proceed with the dashboard
                df_leads = st.session_state.lead_data

                # Filtering Section (now in the sidebar)
                df_filtered, show_lead_analysis, show_monthly_distribution, show_us_map = filtering_section(df_leads)

                # Visualization Sections
                if show_lead_analysis:
                    lead_analysis_charts(df_filtered)
                if show_monthly_distribution:
                    monthly_lead_distribution_chart(df_filtered)
                if show_us_map:
                    us_map_visualization(df_filtered)

                # Filtered Records Table Section
                filtered_records_table(df_filtered)

                # Inject JavaScript to scroll to top after dashboard is loaded
                st.markdown(
                    """
                    <script>
                    window.onload = function() {
                        window.scrollTo(0, 0);
                    };
                    </script>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.warning("No data available to display the dashboard.")

if __name__ == "__main__":
    main()
