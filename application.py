import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import plotly_express as px
import snowflake.connector
import os

#TODO: Find a better way to check if DB connection times out and re-establish 


#############################
## Calculation Settings     
#############################

# Define SQL used for each dimension
sql_formulas = {'Hour of Day':'HOUR',
                'Day of Week':'DATE_PART(dayofweek,CRASHDATE)',
                'Age': 'round(DRIVER1AGE/2,0) *2',
                'Week of Year':'DATE_PART(week,CRASHDATE)'}

# Axis limits for each dimension
dimension_limits = {'Hour of Day':24,
                    'Day of Week':7,
                    'Age': 100,
                    'Week of Year':52}




###########################################
## Snowflake Database Interaction Functions
###########################################

# Open Connection
def SnowDBConnect():
    
    # read credentials from OS enviroment variables
    SNOWFLAKE_USER = os.environ['SNOWFLAKE_USER']
    SNOWFLAKE_PWD = os.environ['SNOWFLAKE_PWD']
    SNOWFLAKE_WAREHOUSE = os.environ['SNOWFLAKE_WAREHOUSE']
    
    # open DB connection
    conn = snowflake.connector.connect(
              user= SNOWFLAKE_USER ,
              password=SNOWFLAKE_PWD,
              account = 'tha74675.us-east-1',
              warehouse=SNOWFLAKE_WAREHOUSE,
              database='MIACCIDENTDATA',
              schema='MIACCIDENT'
              )
    return conn

# Function to query heatmap data
def GetCrosstabData(conn,x_dimension,y_dimension):

    # Get SQL code for X and Y dimensions
    x_dimension_string = sql_formulas.get(x_dimension)
    y_dimension_string = sql_formulas.get(y_dimension)
    
    # Build SQL statement and insert X / Y axis code
    sql = """
    SELECT
    count(X) As COUNT,
    {} As X_AXIS,
    {} As Y_AXIS
    
    FROM GR_CRASH_DATA
    
    GROUP BY
    {},
    {}
    """.format(x_dimension_string,y_dimension_string,x_dimension_string,y_dimension_string)
    # Execute query
    cur = conn.cursor()
    cur.execute(sql)
    # Fetch the result set from the cursor and deliver it as the Pandas DataFrame.
    df = cur.fetch_pandas_all()
    return df

# Function to query map data
def GetSpatialBins(conn,
                   x_filter,
                   y_filter,
                   x_dimension,
                   y_dimension):    
    
        
    # Get SQL code for X and Y dimension filters
    x_filter_string = sql_formulas.get(x_dimension)+" = "+str(x_filter)
    y_filter_string = sql_formulas.get(y_dimension)+" = "+str(y_filter)
    
     # Build SQL statement and insert X / Y axis code
    sql = """
    SELECT
    count(X) As COUNT,
    round(Y/2,3)*2 As LAT_BIN,
    round(X/2,3)*2 As LON_BIN

    
    FROM GR_CRASH_DATA
    
    WHERE
    {}
    and
    {}
    
    GROUP BY
    round(X/2,3)*2,
    round(Y/2,3)*2
    
    HAVING
    count(X) >=1

    """.format(x_filter_string, y_filter_string)
    # Execute query
    cur = conn.cursor()
    cur.execute(sql)
    # Put results in Pandas DF
    df = cur.fetch_pandas_all()
    return df



#########################
## Initiate Application
#########################

# Open Database Conection
db_connection = SnowDBConnect()
 
# Initialize app server
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
application = app.server
app.title='GR Crash Data Viz'



#######################
## App Layout
#######################
app.layout = html.Div([
    dcc.Markdown('''
### Grand Rapids Traffic Accident Heatmap
This data visualization highlights patterns in traffic accidents in the city of Grand Rapids, Michigan.
Data used in this visualization is publically available from [GRData](https://grdata-grandrapids.opendata.arcgis.com/datasets/cgr-crash-data)
. This incredibly rich dataset includes detailed information for 74,309 traffic accidents logged between 2007 and 2017.  

##### Explore relationships between variables and accident counts
Use dropdowns below to explore relationships between age, week of year, day of week, and hour of day.  Click on a square to show accident locations on the map below.
''')  ,
    
    html.Div([
        html.Label(["Horizontal (X) Axis", 
            dcc.Dropdown(
                id = 'x_axis_dimension',
                options=[
                    {'label': 'Week of Year', 'value': 'Week of Year'},
                    {'label': 'Age', 'value': 'Age'},
                    {'label': 'Day of Week', 'value': 'Day of Week'},
                    {'label': 'Hour of Day', 'value': 'Hour of Day'}
                 ],
                value='Week of Year',
                clearable=False
            )
        ],style={'width': '20%',
                       'display': 'inline-block'}),
        html.Label(["Vertical (Y) Axis", 
            dcc.Dropdown(
                id = 'y_axis_dimension',
                options=[
                    {'label': 'Week of Year', 'value': 'Week of Year'},
                    {'label': 'Age', 'value': 'Age'},
                    {'label': 'Day of Week', 'value': 'Day of Week'},
                    {'label': 'Hour of Day', 'value': 'Hour of Day'}
                ],
                value='Hour of Day',
                clearable=False
                
            )
        ],style={'width': '20%',
                       'display': 'inline-block'})
            
    ]),
    dcc.Graph(id='crosstab'),
    dcc.Markdown('''
            ##### Where are these accidents happening?
            Click a square on the heatmap above to see accident locations on the map below
            '''),
    
    dcc.Graph(id='map-plot')

])

##################
## App Calbacks
##################

# Heatmap Callback
@app.callback(Output('crosstab', 'figure'),
[Input('x_axis_dimension', 'value'),
 Input('y_axis_dimension', 'value')])
def update_heatmap(x_axis_dimension, y_axis_dimension):
    global db_connection
    # Query data.  If query fails then re-open connecton and try again
    try:
        crosstab_data = GetCrosstabData(db_connection,
                                    x_dimension = x_axis_dimension,
                                    y_dimension = y_axis_dimension)
    except:
        db_connection = SnowDBConnect()
        crosstab_data = GetCrosstabData(db_connection,
                                    x_dimension = x_axis_dimension,
                                    y_dimension = y_axis_dimension)
    
    # Get reasonable range of values for X and Y axis
    x_axis_limit = dimension_limits.get(x_axis_dimension)
    y_axis_limit = dimension_limits.get(y_axis_dimension) 
    
    # apply value range limits
    crosstab_data = crosstab_data.query("X_AXIS <= @x_axis_limit and Y_AXIS <= @y_axis_limit")
    
    # reshape data
    crosstab_data = crosstab_data.pivot(index='Y_AXIS',
                                        columns='X_AXIS',
                                        values='COUNT').fillna(0)
    
    
    # create heatmap    
    crosstab_plot = px.imshow(crosstab_data,
                              color_continuous_scale='Sunset',
                              aspect = 'auto',
                              range_color=(crosstab_data.to_numpy().min()
                                           ,crosstab_data.to_numpy().max()),
                              labels = {'x':x_axis_dimension,
                                        'y':y_axis_dimension,
                                        'color': 'Accident Count'})
    # remove color scale legend
    crosstab_plot.layout.coloraxis.showscale = False
    # reduce padding
    crosstab_plot.update_layout(margin=dict(l=20, r=20, t=10, b=0))

    return crosstab_plot

# Map Callback
@app.callback(
    Output('map-plot', 'figure'),
    [Input('crosstab', 'clickData'),
     Input('x_axis_dimension', 'value'),
     Input('y_axis_dimension', 'value')]
)
def update_map(clickData, x_axis_dimension, y_axis_dimension):
    
    if clickData: # if the user has clicked the heatmap then
        #query map data
        spatial_data = GetSpatialBins(db_connection,
                                  x_filter =clickData['points'][0]['x'],
                                  y_filter = clickData['points'][0]['y'],
                                  x_dimension = x_axis_dimension,
                                  y_dimension = y_axis_dimension)
        # build map plot
        map_plot = px.scatter_mapbox(spatial_data,
                                lat="LAT_BIN",
                                lon="LON_BIN",
                                color="COUNT",
                                size="COUNT",
                                color_continuous_scale=px.colors.sequential.Sunset,
                                range_color=(spatial_data.COUNT.min(),
                                             spatial_data.COUNT.max()),
                                size_max=15,
                                zoom=10)
        # change setting to preserve map zoom and center on update
        map_plot.update_layout(uirevision = True)
        
    else: # If no data is selected then build a blank placeholder map to return
        #TODO: There must be a better way to create a blank maps\
    
        # single point dataframe for placeholder map
        sample_data = pd.DataFrame(data={'LAT': [42.96],
                                         'LON': [-85.67],
                                         'COUNT': [5]})
        # Build blank placeholder map
        map_plot = px.scatter_mapbox(sample_data,
                                     lat='LAT',
                                     lon='LON',
                                     color='COUNT',
                                     size='COUNT',
                                     size_max = 1,
                                     color_continuous_scale=px.colors.sequential.Sunset,
                                     zoom = 10)
        
    # change map style and padding settings    
    map_plot.update_layout(mapbox_style="carto-positron",
                           margin=dict(l=20, r=20, t=10, b=0))
    return map_plot



###############
## Run the app
###############

if __name__ == '__main__':
    application.run(debug=True, port=8080)