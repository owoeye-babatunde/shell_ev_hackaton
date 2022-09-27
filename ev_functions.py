def calculate_Distij(demand_point_x=dfdemand['x_coordinate'], 
                    demand_point_y=dfdemand['y_coordinate'],
                    supply_point_x = dfinfra['x_coordinate'],
                    supply_point_y=dfinfra['y_coordinate']): 
    
     """
    Calculate the distances between ith Demand point and jth supply(Distij) point using
    by evalusting the squareroot of the squared differences between every ith supply piont
    and a jth Demand point
    
    inputs:{array}
        demand_point_x: X coordinate of the demand point. a fixed X coord point that we are 
        calculating the other X coordinate distances with respect to.
        demand_point_y: Y coordinate of the demand point. a fixed Y coord point that we are 
        calculating the other Y coordinate distances with respect to
    
        supply_point_x: X coordinate of ith supply point which we want to map to the demand 
        point
        supply_point_y: Y coordinate of ith supply point which we want to map to the demand 
        point
    
    Returns:{array}
        returns the distance matrix(Distij) of all ith supply points to every jth demand point
    """
    
    
 
    
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
    """
    selects the ith supply points with the minimum K(specified) distances
    to jth demand point
    
    inputs:{array}
        x: a numpy array containing the distance matrices(Distij matrix)
        k: the number of minimum ith supply point distances that we are 
        interested in
    
        inplace{optional}: 
            default: False specifies the minimum distances out of place
                 False specifies the minimum distances in place
    
    Returns:{array}
        true value of the K minimum distances and zero for the rest, note that 
        their original indices are retained for this operation
    """
    
    
    
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
    """
    sums up the distances of ith supply point over all other demand point
    
    input: None
    output{array}: an array of 100 values representing the overall minimum K 
            total distances of ith supply point to every demand point
    
    """
    
    real_sum = []
    for i in range(4096):
        real_sum.append(min_k[i].sum())
        
    sum_dist = np.asarray(real_sum)[:, None]
    return sum_dist


def supply_demand(Dforecast=dfdemand['2018'].values[:, None]):  
    """
    distribute the forecasted demand for a jth Demand point to
    every minimun K supply point in a proportion of their distances
    to the jth demand point.the closer the ith supply point to the jth demand point,
    the more the demand value allocated to the ith supply point
        
    inputs:
    
    Dforecast{array}: This is the forecasted demands for a particular year
    
    Return:
        demand satisfied{array} by each ith supply point with respect to jth
        demand point
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
    calculates the number of additional infrastructure 
    needed at every(100) ith supply points that will make it satisfy the 
    forecasted demand allocated to it by the jth demand point.
    Particularly optimizing for more FCS if more infrastructure is
    needed to reduce the chances of the total infrastructure(FCS + SCS) 
    exceeding the total parking spot
    
    This function particularly satisfy constraint 3 that states that 
    (FCS + SCS) at ith supply point must be greater or equals to the total
    parking slots available, as designed by real estates{constant}
    
    inputs:
       Dforecast{array}:
        This is the forecasted demands for a particular year
     also makes use of some predefined functions
     
     output:
         an array of numbers of additional fast charging stations necessary to
         satisfy the forecasted demand at every ith supply points
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
    """calculates the additional or excess capacity that must be available by
        any ith supply point, provided that its parking capacity is not able to 
        meet the forecasted demand value. This excess capacities must be removed 
        from the demand forecasted for the ith supply points.
        This is a step to fish out the supply points that get too much forecasted
        demand values. So as to not violate constraint number 5 
       
       inputs:
            Dforecast{array}:
            This is the forecasted demands for a particular year
     also makes use of some predefined functions
     
     outputs: 
             excess capacities
    """
    
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
    """
       adjusts the forecast for each ith demand point by subtracting
       the excess capacities or demand value detected by any jth supply 
       point from the overall forecasted demand for the ith supply point
       so as to completely satisfy constraint number 5 which states that
        demand satisfied by each jth supply point must be less than or equal to the
        maximum supply available.
         This is more like a gradient descent step. But in this case, a
         demand descent step.
       inputs:
               Dforecast{array}:
                    This is the forecasted demands for a particular year
               k{int}: minimum Kth of ith supply point distances that we are 
                   interested in
       outputs: {array}
               the adjusted or descent forecast that satisfy constraints
    """
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


def supply_count(min_k):
    """
    gets the count of occurrence of ith supply point over 
    all the demand point
    
    input: {array}
          an array containing the minimum kth distances that
          we are interested in
          
    output: {list}
           a list containing the K number of occurences of the ith
           supply point we are interested in
    
    """
   
    
    kth = min_k.reshape(100, -1)
    lis = []
    for i in range(len(kth)):
        lis.append(len(np.unique(kth[i])))
        
    return np.asarray(lis)

