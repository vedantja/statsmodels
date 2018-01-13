import numpy as np
from statsmodels.regression.bayes_mixed_glm import (
    BinomialBayesMixedGLM, PoissonBayesMixedGLM)
import pandas as pd
from distutils.version import LooseVersion
import scipy
from scipy import sparse
from numpy.testing import assert_allclose
from scipy.optimize import approx_fprime


def gen_simple_logit(nc, cs, s):

    np.random.seed(3799)

    exog_vc = np.kron(np.eye(nc), np.ones((cs, 1)))
    exog_fe = np.random.normal(size=(nc*cs, 2))
    vc = s*np.random.normal(size=nc)
    lp = np.dot(exog_fe, np.r_[1, -1]) + np.dot(exog_vc, vc)
    pr = 1 / (1 + np.exp(-lp))
    y = 1*(np.random.uniform(size=nc*cs) < pr)
    ident = np.zeros(nc, dtype=np.int)

    return y, exog_fe, exog_vc, ident


def gen_simple_poisson(nc, cs, s):

    np.random.seed(3799)

    exog_vc = np.kron(np.eye(nc), np.ones((cs, 1)))
    exog_fe = np.random.normal(size=(nc*cs, 2))
    vc = s*np.random.normal(size=nc)
    lp = np.dot(exog_fe, np.r_[0.1, -0.1]) + np.dot(exog_vc, vc)
    r = np.exp(lp)
    y = np.random.poisson(r)
    ident = np.zeros(nc, dtype=np.int)

    return y, exog_fe, exog_vc, ident


def gen_crossed_logit(nc, cs, s1, s2):

    np.random.seed(3799)

    a = np.kron(np.eye(nc), np.ones((cs, 1)))
    b = np.kron(np.ones((cs, 1)), np.eye(nc))
    exog_vc = np.concatenate((a, b), axis=1)

    exog_fe = np.random.normal(size=(nc*cs, 1))
    vc = s1 * np.random.normal(size=2*nc)
    vc[nc:] *= s2 / s1
    lp = np.dot(exog_fe, np.r_[-0.5]) + np.dot(exog_vc, vc)
    pr = 1 / (1 + np.exp(-lp))
    y = 1*(np.random.uniform(size=nc*cs) < pr)
    ident = np.zeros(2*nc, dtype=np.int)
    ident[nc:] = 1

    return y, exog_fe, exog_vc, ident


def gen_crossed_poisson(nc, cs, s1, s2):

    np.random.seed(3799)

    a = np.kron(np.eye(nc), np.ones((cs, 1)))
    b = np.kron(np.ones((cs, 1)), np.eye(nc))
    exog_vc = np.concatenate((a, b), axis=1)

    exog_fe = np.random.normal(size=(nc*cs, 1))
    vc = s1 * np.random.normal(size=2*nc)
    vc[nc:] *= s2 / s1
    lp = np.dot(exog_fe, np.r_[-0.5]) + np.dot(exog_vc, vc)
    r = np.exp(lp)
    y = np.random.poisson(r)
    ident = np.zeros(2*nc, dtype=np.int)
    ident[nc:] = 1

    return y, exog_fe, exog_vc, ident


def gen_crossed_logit_pandas(nc, cs, s1, s2):

    np.random.seed(3799)

    a = np.kron(np.arange(nc), np.ones(cs))
    b = np.kron(np.ones(cs), np.arange(nc))
    fe = np.ones(nc * cs)

    vc = np.zeros(nc * cs)
    for i in np.unique(a):
        ii = np.flatnonzero(a == i)
        vc[ii] += s1*np.random.normal()
    for i in np.unique(b):
        ii = np.flatnonzero(b == i)
        vc[ii] += s2*np.random.normal()

    lp = -0.5 * fe + vc
    pr = 1 / (1 + np.exp(-lp))
    y = 1*(np.random.uniform(size=nc*cs) < pr)

    ident = np.zeros(2*nc, dtype=np.int)
    ident[nc:] = 1

    df = pd.DataFrame({"fe": fe, "a": a, "b": b, "y": y})

    return df


def test_simple_logit_map():

    y, exog_fe, exog_vc, ident = gen_simple_logit(10, 10, 2)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                 vcp_p=0.5)
    rslt = glmm.fit_map()

    assert_allclose(glmm.logposterior_grad(rslt.params),
                    np.zeros_like(rslt.params), atol=1e-3)


def test_simple_poisson_map():

    y, exog_fe, exog_vc, ident = gen_simple_poisson(10, 10, 0.2)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm1 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                 vcp_p=0.5)
    rslt1 = glmm1.fit_map()
    assert_allclose(glmm1.logposterior_grad(rslt1.params),
                    np.zeros_like(rslt1.params), atol=1e-3)

    # This should give the same answer as above
    glmm2 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                 vcp_p=0.5)
    rslt2 = glmm2.fit_map()
    assert_allclose(rslt1.params, rslt2.params, atol=1e-4)


def test_crossed_logit_map():

    y, exog_fe, exog_vc, ident = gen_crossed_logit(10, 10, 1, 2)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                 vcp_p=0.5)
    rslt = glmm.fit_map()

    assert_allclose(glmm.logposterior_grad(rslt.params),
                    np.zeros_like(rslt.params), atol=1e-4)


def test_crossed_poisson_map():

    y, exog_fe, exog_vc, ident = gen_crossed_poisson(10, 10, 1, 1)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                vcp_p=0.5)
    rslt = glmm.fit_map()

    assert_allclose(glmm.logposterior_grad(rslt.params),
                    np.zeros_like(rslt.params), atol=1e-4)


def test_logit_map_crossed_formula():

    data = gen_crossed_logit_pandas(10, 10, 1, 0.5)

    fml = "y ~ fe"
    fml_vc = ["0 + C(a)", "0 + C(b)"]
    glmm = BinomialBayesMixedGLM.from_formula(
        fml, fml_vc, data, vcp_p=0.5)
    rslt = glmm.fit_map()

    assert_allclose(glmm.logposterior_grad(rslt.params),
                    np.zeros_like(rslt.params), atol=1e-4)

    rslt.summary()

    if LooseVersion(scipy.__version__) >= LooseVersion("0.19.0"):
        r = rslt.random_effects(0)
        assert_allclose(r.iloc[0, :].values,
                        np.r_[-0.02004904, 0.10013856], atol=1e-4)


def test_elbo_grad():

    for f in range(2):
        for j in range(2):

            if f == 0:
                if j == 0:
                    y, exog_fe, exog_vc, ident = gen_simple_logit(10, 10, 2)
                else:
                    y, exog_fe, exog_vc, ident = gen_crossed_logit(
                        10, 10, 1, 2)
            elif f == 1:
                if j == 0:
                    y, exog_fe, exog_vc, ident = gen_simple_poisson(
                        10, 10, 0.5)
                else:
                    y, exog_fe, exog_vc, ident = gen_crossed_poisson(
                        10, 10, 1, 0.5)

            exog_vc = sparse.csr_matrix(exog_vc)

            if f == 0:
                glmm1 = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                              vcp_p=0.5)
            else:
                glmm1 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident,
                                             vcp_p=0.5)

            rslt1 = glmm1.fit_map()

            for k in range(3):

                if k == 0:
                    vb_mean = rslt1.params
                    vb_sd = np.ones_like(vb_mean)
                elif k == 1:
                    vb_mean = np.zeros(len(vb_mean))
                    vb_sd = np.ones_like(vb_mean)
                else:
                    vb_mean = np.random.normal(size=len(vb_mean))
                    vb_sd = np.random.uniform(1, 2, size=len(vb_mean))

                mean_grad, sd_grad = glmm1.vb_elbo_grad(vb_mean, vb_sd)

                def elbo(vec):
                    n = len(vec) // 2
                    return glmm1.vb_elbo(vec[:n], vec[n:])

                x = np.concatenate((vb_mean, vb_sd))
                g1 = approx_fprime(x, elbo, 1e-5)
                n = len(x) // 2

                mean_grad_n = g1[:n]
                sd_grad_n = g1[n:]

                assert_allclose(mean_grad, mean_grad_n, atol=1e-2,
                                rtol=1e-2)
                assert_allclose(sd_grad, sd_grad_n, atol=1e-2,
                                rtol=1e-2)


def test_simple_logit_vb():

    y, exog_fe, exog_vc, ident = gen_simple_logit(10, 10, 0)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm1 = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                  fe_p=0.5)
    rslt1 = glmm1.fit_map()

    glmm2 = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                  fe_p=0.5)
    rslt2 = glmm2.fit_vb(rslt1.params)

    rslt1.summary()
    rslt2.summary()

    assert_allclose(rslt1.params[0:5], np.r_[
        0.75330405, -0.71643228, -2.49091288, -0.00959806,  0.00450254],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.params[0:5], np.r_[
        0.79338836, -0.7599833, -0.64149356, -0.24772884,  0.10775366],
                    rtol=1e-4, atol=1e-4)


def test_simple_poisson_vb():

    y, exog_fe, exog_vc, ident = gen_simple_poisson(10, 10, 1)
    exog_vc = sparse.csr_matrix(exog_vc)

    glmm1 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5)
    rslt1 = glmm1.fit_map()

    glmm2 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5)
    rslt2 = glmm2.fit_vb(rslt1.params)

    rslt1.summary()
    rslt2.summary()

    assert_allclose(rslt1.params[0:5], np.r_[
        -0.07233493, -0.06706505, -0.47159649,  1.12575122, -1.02442201],
                    rtol=1e-4, atol=1e-4)

    if LooseVersion(scipy.__version__) < LooseVersion("0.19.0"):
        return

    assert_allclose(rslt1.cov_params.flat[0:5], np.r_[
        0.00737842, 0.0012137, -0.00033823, -0.00029894,  0.00072396],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.params[0:5], np.r_[
        -0.07088814, -0.06373107, -0.22770786,  1.12923746, -1.26161339],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.cov_params[0:5], np.r_[
        0.00747782, 0.0092554, 0.04508904, 0.02934488, 0.20312746],
                    rtol=1e-4, atol=1e-4)


def test_crossed_logit_vb():

    y, exog_fe, exog_vc, ident = gen_crossed_logit(10, 10, 1, 2)

    glmm1 = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                  fe_p=0.5)
    rslt1 = glmm1.fit_map()

    glmm2 = BinomialBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                  fe_p=0.5)
    rslt2 = glmm2.fit_vb(mean=rslt1.params)

    rslt1.summary()
    rslt2.summary()

    assert_allclose(rslt1.params[0:5], np.r_[
        -5.43073978e-01, -2.46197518e+00, -2.36582801e+00,
        -9.64030461e-03, 2.32701078e-03],
                    rtol=1e-4, atol=1e-4)

    if LooseVersion(scipy.__version__) < LooseVersion("0.19.0"):
        return

    assert_allclose(rslt1.cov_params.flat[0:5], np.r_[
        0.03937444, 0.00218164, 0.00599386, 0.00039312, 0.00017214],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.params[0:5], np.r_[
        -0.70834417, -0.3571011, 0.19126823, -0.36074489, 0.058976],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.cov_params[0:5], np.r_[
        0.05212492, 0.04729656, 0.03916944, 0.25921842, 0.25782576],
                    rtol=1e-4, atol=1e-4)


def test_crossed_logit_vb_formula():

    data = gen_crossed_logit_pandas(10, 10, 1, 2)

    fml = "y ~ fe"
    fml_vc = ["0 + C(a)", "0 + C(b)"]
    glmm1 = BinomialBayesMixedGLM.from_formula(
        fml, fml_vc, data, vcp_p=0.5)
    rslt1 = glmm1.fit_vb()

    glmm2 = BinomialBayesMixedGLM(glmm1.endog, glmm1.exog_fe, glmm1.exog_vc,
                                  glmm1.ident, vcp_p=0.5)
    rslt2 = glmm2.fit_vb()

    assert_allclose(rslt1.params, rslt2.params, atol=1e-4)

    rslt1.summary()
    rslt2.summary()


def test_crossed_poisson_vb():

    y, exog_fe, exog_vc, ident = gen_crossed_poisson(10, 10, 1, 0.5)

    glmm1 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                 fe_p=0.5)
    rslt1 = glmm1.fit_map()

    glmm2 = PoissonBayesMixedGLM(y, exog_fe, exog_vc, ident, vcp_p=0.5,
                                 fe_p=0.5)
    rslt2 = glmm2.fit_vb(mean=rslt1.params)

    rslt1.summary()
    rslt2.summary()

    assert_allclose(rslt1.params[0:5], np.r_[
        -0.54855281, 0.10458834, -0.68777741, -0.01699925, 0.77200546],
                    rtol=1e-4, atol=1e-4)

    assert_allclose(rslt2.params[0:5], np.r_[
        -0.54691502, 0.22297158, -0.52673802, -0.06218684, 0.74385237],
                    rtol=1e-4, atol=1e-4)
