import numpy

def squared_hinge_deriv(x):
    return numpy.where(x<1, 2*(x-1), 0)

def mmir(unscaled_features, limits, unscaled_starting=None, 
         threshold=1e-3, verbose=0, max_iterations=1e4):
    """Max Margin Interval Regression using the squared hinge loss.

    We assume that each row of limits is (L_i^left,L_i^right), the
    target interval of the real line which corresponds to zero
    error. The squared hinge loss phi(L) is convex and differentiable
    so we use an accelerated gradient descent solver. First we
    normalize the feature matrix, giving standardized features x_i in
    R^p. Then we use an affine function f(x_i)=w'x_i+b to predict an L
    value that falls between the limits L_i^left and L_i^right. So the
    optimization problem is: min_{b,w} 1/n * sum_i
    phi[f(x_i)-L_i^left] + phi[L_i^right-f(x_i)]. The optimization
    stops when we find an optimization variable for which each
    dimension is within a threshold of the gradient optimality
    condition.

    Useful equations for optimization. The scaled variables are used
    in the optimization problem, but the unscaled variables are
    returned to the user.

    unscaled_intercept = scaled_intercept - sum{j=1}^p w_j mu_j/sigma_j.

    unscaled_weight_j = scaled_weight_j/sigma_j for every variable j.

    """
    assert type(unscaled_features) == numpy.ndarray
    assert type(limits) == numpy.ndarray
    feat_nrow, feat_ncol = unscaled_features.shape
    lim_nrow, lim_ncol = limits.shape
    assert feat_nrow == lim_nrow
    assert feat_nrow > 1
    assert lim_ncol == 2
    mu = unscaled_features.mean(axis=0)
    centered = unscaled_features - mu
    # unbiased variance estimate like R.
    normalization = feat_nrow/(feat_nrow-1)
    sigma = numpy.sqrt(centered.var(axis=0)*normalization)
    features = centered/sigma
    nvars = feat_ncol+1
    # the first element of starting_iterate=[b,w_1,w_2] is the
    # intercept, the others are weights.
    if unscaled_starting is None:
        starting_iterate = numpy.zeros(nvars)
    else:
        unscaled_intercept, unscaled_weights = unscaled_starting
        intercept_term = [unscaled_intercept + (unscaled_weights*mu).sum()]
        weight_term = unscaled_weights*sigma
        #print intercept_term, weight_term
        tup = (intercept_term,weight_term)
        starting_iterate = numpy.concatenate(tup)
    assert len(starting_iterate)==nvars
    # Lipshitz constant from the Flamary et al 2012 appendix.
    #Lipschitz = (features * features).sum()/feat_nrow
    Lipschitz = 2*feat_ncol
    def calc_grad(x):
        linear_predictor = features.dot(x[1:]) + x[0]
        left = squared_hinge_deriv(linear_predictor - limits[:,0])
        right = squared_hinge_deriv(limits[:,1]-linear_predictor)
        diff_term = left - right
        weight_term = features.transpose().dot(diff_term)
        full_grad = numpy.concatenate(([diff_term.sum()],weight_term))
        return full_grad/feat_nrow
    def pL(x):
        """From the FISTA paper."""
        grad = calc_grad(x)
        return x - grad/Lipschitz
    iterate_count = 1
    stopping_crit = threshold
    this_iterate = starting_iterate
    y = starting_iterate
    this_t = 1
    while stopping_crit >= threshold:
        last_iterate = this_iterate
        this_iterate = pL(y)
        last_t = this_t
        this_t = (1+numpy.sqrt(1+4*last_t*last_t))/2
        y = this_iterate + (last_t - 1)/this_t*(this_iterate-last_iterate)
        after_grad = calc_grad(this_iterate)
        zero_at_optimum = numpy.abs(after_grad)
        stopping_crit = zero_at_optimum.max()
        if verbose >= 1:
            print "%10d crit %10.7f"%(iterate_count, stopping_crit)
        iterate_count += 1
        if iterate_count > max_iterations:
            print "%d iterations"%iterate_count
            # need to return a good solution, even if optimization
            # fails. So return the last optimal solution.
            return unscaled_starting
    weights = this_iterate[1:]/sigma
    intercept = this_iterate[0]-(this_iterate[1:]*mu/sigma).sum()
    return intercept, weights

if __name__ == "__main__":
    X = numpy.fromfile("X.csv",sep=" ")
    X = X.reshape(len(X)/2, 2)
    L = numpy.fromfile("L.csv",sep=" ")
    L = L.reshape(len(L)/2, 2)
    intercept, weights = mmir(X,L,verbose=1)
    coefs = numpy.concatenate(([intercept],weights))
    coefs.tofile("coefs-python.csv",sep=" ")
