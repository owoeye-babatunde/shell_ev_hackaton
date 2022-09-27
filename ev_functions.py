def calculate_Distij(demand_point_x=dfdemand['x_coordinate'], 
                    demand_point_y=dfdemand['y_coordinate'],
                    supply_point_x = dfinfra['x_coordinate'],
                    supply_point_y=dfinfra['y_coordinate']): 
    # for x coord
    newdf = pd.DataFrame()
    lis = []
    for i in demand_point_x:
        for j in supply_point_x:
            lis.append(i-j)
    lisarr = np.asarray(lis)
    #print(lisarr)
    # for y coord
    lis1 = []
    for i in demand_point_y:
        for j in supply_point_y:
            lis1.append(i-j)
    lisarr1 = np.asarray(lis1)
    lis2 = []
    #Calculating linear distances between two points
    for x, y in zip(lisarr, lisarr1):
        lis2.append(np.sqrt(x**2 + y**2))
    Distij = np.asarray(lis2)
    #dist1 is the copy of the reshaped dist value
    Distij = Distij.reshape(4096, 100)
    #print(dist1.shape)
    return Distij



def truncate_min_k(x, k, inplace=False):
    m, n = x.shape
    # get (unsorted) indices of top-k values
    mink_indices = np.argpartition(x, k, axis=1)[:, :k]
    # get k-th value
    rows, _ = np.indices((m, k))
    kth_vals = x[rows, mink_indices].max(axis=1)
    # get boolean mask of values smaller than k-th
    is_greater_than_kth = x > kth_vals[:, None]
    # replace mask by 0
    if not inplace:
        return np.where(is_greater_than_kth, 0, x)
    x[is_greater_than_kth] = 0
    return x

min_k = truncate_min_k(x, k=k)


def summation_Dist():
    real_sum = []
    for i in range(4096):
        real_sum.append(min_k[i].sum())
        
    sum_dist = np.asarray(real_sum)[:, None]
    return sum_dist


def supply_demand(Dforecast=dfdemand['2018'].values[:, None]):  
    """
    Constraint5: 
    inputs:
    trunmin: This is the truncated minimum distances of each demand points from
    every supply points
    di: This is the forecasted demands for a particular year
    sum_dist: This is the sum of the truncated distances of each demand point from every 
    supply points reshaped into 4096 X 1 to match the broadcastable shape of 'trunmin'
    
    Return:
        demand satisfied by each supply point by the demand point
    """
    sum_dist = summation_Dist()
    min_k = truncate_min_k(x, k).reshape(4096, -1)    
    lis = []
    for j in range(4096):
        for distance in min_k[j]: #changed to minfive
            #for x, y, z in zip(min_sup, sum_dist[0], di[0]):
              #  lis.append((x*z)/y)
            lis.append((distance*Dforecast[j])/sum_dist[j])
 
    
    return np.asarray(lis)



dfinfra['scs_cap'] = dfinfra['existing_num_SCS']*200
dfinfra['fcs_cap'] = dfinfra['existing_num_FCS']*400
dfinfra['total_cap'] = dfinfra['scs_cap']+ dfinfra['fcs_cap']
dfinfra['parking_cap'] = (dfinfra['total_parking_slots'] - dfinfra['existing_num_SCS']) * 400 + (dfinfra['existing_num_SCS']) * 200
dfinfra['available_cap'] = dfinfra['parking_cap'] - dfinfra['total_cap']


def add_infrastructure(Dforecast=dfdemand['2018'].values[:, None]):
    """
    purpose: This function calculates the number of additional infrastructure 
    needed at every(100) supply points over all the demand points.
    Particularly optimizing for more FCS if more infrastructure is
    needed
    inputs:
    sup_cap:
    This is the overall calculated supply capacity returned by our model(calculation parameters)
    scs_cap{constant}:
    This is the supply or charging capacity of slow charging station at every supply point
    const_total{constant}:
    This is the constant total charging capacity at every supply point
    """
    newval =  supply_demand(Dforecast)
    newval = newval.reshape(100, -1)
    DS = np.sum(newval, 1)
    smax= dfinfra['total_cap'].values
    lis = []# for fast charging stations
    for DSij, Smax in zip(DS, smax):
    
        result = Smax - DSij
        if result >= 0:
            lis.append(0)
        else:
            result = abs(result)
            lis.append((result//400) + 1) #+1 removed

        
    
    more_infra = np.asarray(lis) # capacity to add
    return more_infra




def excess_charging_cap(Dforecast=dfdemand['2018'].values[:, None], k=k):
    #dfinfra['new_FCS'] = dfinfra['existing_num_FCS'].values + to_add
    to_add = add_infrastructure(Dforecast)
    dfinfra['add_cap'] = to_add * 400
    dfinfra['excess_cap'] = dfinfra['available_cap'] - dfinfra['add_cap']
    #print(dfinfra['excess_cap'])
    excess=[]
    for i in dfinfra['excess_cap']:
        if i >= 0:
            excess.append(0)
        elif i < 0:
            excess.append(i)
    excess = np.asarray(excess)
    #print(len(excess))
    return excess




dfinfra['new_FCS'] = dfinfra['existing_num_FCS'].values + to_add
dfinfra['new_FCS_cap'] = dfinfra['new_FCS'] * 400
dfinfra['excess_charge_cap'] = dfinfra['parking_cap'] - (dfinfra['scs_cap'] + dfinfra['new_FCS_cap'])
dfinfra['excess_charge_cap'].values



def adjusted_forecast(Dforecast=dfdemand['2018'].values[:, None], k=k):
    parking_cap = dfinfra['parking_cap'].values
    parking_cap.shape
    excess_cap = dfinfra['excess_charge_cap'].values
    excess = excess_charging_cap(Dforecast, k=k)
    newval =  supply_demand().reshape(100, -1)
    #print(newval)
    max_sup_cap = []
    
    for i in range(len(excess)):
        div_factor = excess[i]/(4096)
        #print(div_factor)
        max_sup_cap.append(newval[i] + div_factor)
    max_sup_cap = np.asarray(max_sup_cap)#.reshape(4096, -1)
    
    forecasted = []
    for i in range(4096):
        for cap in max_sup_cap:
            forecasted.append(cap[i])
    forecasted = np.asarray(forecasted)
    return forecasted



