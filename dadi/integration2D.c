#include "integration_shared.h"
#include "tridiag.h"

void implicit_2Dx(int L, int M; // gcc's 'forward declarations'
        double phi[L][M], double xx[L], double yy[M],
        double nu1, double m12, double gamma1, 
        double dt, int L, int M, int use_delj_trick){
    int ii, jj;

    double dx[L-1], dfactor[L], xInt[L-1];
    compute_dx(xx, L, dx);
    compute_dfactor(dx, L, dfactor);
    compute_xInt(xx, L, xInt);
    
    double Mfirst, Mlast;
    double MInt[L-1], V[L], VInt[L-1];
    double delj[L-1];
    for(ii=0; ii < L; ii++)
        V[ii] = Vfunc(xx[ii], nu1);
    for(ii=0; ii < L-1; ii++)
        VInt[ii] = Vfunc(xInt[ii], nu1);

    double a[L], b[L], c[L], r[L], temp[L];
    double y;
    for(jj=0; jj < M; jj++){
        y = yy[jj];

        Mfirst = Mfunc2D(xx[0], y, m12, gamma1);
        Mlast = Mfunc2D(xx[L-1], y, m12, gamma1);
        for(ii=0; ii < L-1; ii++)
            MInt[ii] = Mfunc2D(xInt[ii], y, m12, gamma1);

        compute_delj(dx, MInt, VInt, L, delj, use_delj_trick);
        compute_abc_nobc(dx, dfactor, delj, MInt, V, dt, L, a, b, c);
        for(ii = 0; ii < L; ii++)
            r[ii] = phi[ii][jj]/dt;

        if((jj==0) && (Mfirst <= 0))
            b[0] += (0.5/nu1 - Mfirst)*2./dx[0];
        if((jj==M-1) && (Mlast >= 0))
            b[L-1] += -(-0.5/nu1 - Mlast)*2./dx[L-2];

        tridiag(a, b, c, r, temp, L);
        for(ii = 0; ii < L; ii++)
            phi[ii][jj] = temp[ii];
    }
}

void implicit_2Dy(int L, int M;
        double phi[L][M], double xx[L], double yy[M],
        double nu2, double m21, double gamma2, 
        double dt, int L, int M, int use_delj_trick){
    int ii, jj;

    double dy[M-1], dfactor[M], yInt[M-1];
    compute_dx(yy, M, dy);
    compute_dfactor(dy, M, dfactor);
    compute_xInt(yy, M, yInt);
    
    double Mfirst, Mlast;
    double MInt[M-1], V[M], VInt[M-1];
    double delj[M-1];
    for(jj=0; jj < M; jj++)
        V[jj] = Vfunc(yy[jj], nu2);
    for(jj=0; jj < M-1; jj++)
        VInt[jj] = Vfunc(yInt[jj], nu2);

    double a[M], b[M], c[M], r[M];
    double x;
    for(ii=0; ii < L; ii++){
        x = xx[ii];

        Mfirst = Mfunc2D(yy[0], x, m21, gamma2);
        Mlast = Mfunc2D(yy[M-1], x, m21, gamma2);
        for(jj=0; jj < M-1; jj++)
            MInt[jj] = Mfunc2D(yInt[jj], x, m21, gamma2);

        compute_delj(dy, MInt, VInt, M, delj, use_delj_trick);
        compute_abc_nobc(dy, dfactor, delj, MInt, V, dt, M, a, b, c);
        for(jj = 0; jj < M; jj++)
            r[jj] = phi[ii][jj]/dt;

        if((ii==0) && (Mfirst <= 0))
            b[0] += (0.5/nu2 - Mfirst)*2./dy[0];
        if((ii==L-1) && (Mlast >= 0))
            b[M-1] += -(-0.5/nu2 - Mlast)*2./dy[M-2];

        tridiag(a, b, c, r, phi[ii], M);
    }
}

void implicit_precalc_2Dx(int M, int L; // gcc's "forward-declarations" 
        double phi[L][M], 
        double ax[L][M], double bx[L][M], double cx[L][M],
        double dt, int L, int M){
    /* Warning: The bx passed in here should *not* include the 1/dt
     * contribution.
     */
    int ii, jj;

    double a[L], b[L], c[L], r[L], temp[L];
    for(jj=0; jj < M; jj++){
        for(ii = 0; ii < L; ii++){
            // Annoyingly, we need to create copies of the columns to pass to
            // tridiag.
            a[ii] = ax[ii][jj];
            b[ii] = bx[ii][jj] + 1/dt;
            c[ii] = cx[ii][jj];
            r[ii] = 1/dt * phi[ii][jj];
        }

        tridiag(a, b, c, r, temp, L);
        for(ii = 0; ii < L; ii++)
            phi[ii][jj] = temp[ii];
    }
}

void implicit_precalc_2Dy(int L, int M;
        double phi[L][M], 
        double ay[L][M], double by[L][M], double cy[L][M],
        double dt, int L, int M){
    int ii, jj;

    double b[M], r[M]; 

    for(ii = 0; ii < L; ii++){
        for(jj = 0; jj < M; jj++){
            b[jj] = by[ii][jj] + 1/dt;
            r[jj] = 1/dt * phi[ii][jj];
        }

        tridiag(ay[ii], b, cy[ii], r, phi[ii], M);
    }
}
