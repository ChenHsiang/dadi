"""
Miscellaneous utility functions. Including ms simulation.
"""

import os,sys,time

import numpy
import scipy.linalg

# Nucleotide order assumed in Q matrices.
code = 'CGTA'

#: Storage for times at which each stream was flushed.
__times_last_flushed = {}
def delayed_flush(stream=sys.stdout, delay=1):
    """
    Flush a stream, ensuring that it is only flushed every 'delay' *minutes*.
    Note that upon the first call to this method, the stream is not flushed.

    stream: The stream to flush. For this to work with simple 'print'
            statements, the stream should be sys.stdout.
    delay: Minimum time *in minutes* between flushes.

    This function is useful to prevent I/O overload on the cluster.
    """
    global __times_last_flushed

    curr_time = time.time()
    # If this is the first time this method has been called with this stream,
    # we need to fill in the times_last_flushed dict. setdefault will do this
    # without overwriting any entry that may be there already.
    if stream not in __times_last_flushed:
        __times_last_flushed[stream] = curr_time
    last_flushed = __times_last_flushed[stream]

    # Note that time.time() returns values in seconds, hence the factor of 60.
    if (curr_time - last_flushed) >= delay*60:
        stream.flush()
        __times_last_flushed[stream] = curr_time

def ensure_1arg_func(var):
    """
    Ensure that var is actually a one-argument function.

    This is primarily used to convert arguments that are constants into
    trivial functions of time for use in integrations where parameters are
    allowed to change over time.
    """
    if numpy.isscalar(var):
        # If a constant was passed in, use lambda to make it a nice
        #  simple function.
        var_f = lambda t: var
    else:
        var_f = var
    if not callable(var_f):
        raise ValueError('Argument is not a constant or a function.')
    try:
        var_f(0.0)
    except TypeError:
        raise ValueError('Argument is not a constant or a one-argument '
                         'function.')
    return var_f

def ms_command(theta, ns, core, iter, recomb=0, rsites=None):
    """
    Generate ms command for simulation from core.

    theta: Assumed theta
    ns: Sample sizes
    core: Core of ms command that specifies demography.
    iter: Iterations to run ms
    recomb: Assumed recombination rate
    rsites: Sites for recombination. If None, default is 10*theta.
    """
    if len(ns) > 1:
        ms_command = "ms %(total_chrom)i %(iter)i -t %(theta)f -I %(numpops)i "\
                "%(sample_sizes)s %(core)s"
    else:
        ms_command = "ms %(total_chrom)i %(iter)i -t %(theta)f  %(core)s"

    if recomb:
        ms_command = ms_command + " -r %(recomb)f %(rsites)i"
        if not rsites:
            rsites = theta*10
    sub_dict = {'total_chrom': numpy.sum(ns), 'iter': iter, 'theta': theta,
                'numpops': len(ns), 'sample_sizes': ' '.join(map(str, ns)),
                'core': core, 'recomb': recomb, 'rsites': rsites}

    return ms_command % sub_dict

def perturb_params(params, fold=1, lower_bound=None, upper_bound=None):
    """
    Generate a perturbed set of parameters.

    Each element of params is radomly perturbed <fold> factors of 2 up or down.
    fold: Number of factors of 2 to perturb by
    lower_bound: If not None, the resulting parameter set is adjusted to have 
                 all value greater than lower_bound.
    upper_bound: If not None, the resulting parameter set is adjusted to have 
                 all value less than upper_bound.
    """
    pnew = params * 2**(fold * (2*numpy.random.random(len(params))-1))
    if lower_bound is not None:
        for ii,bound in enumerate(lower_bound):
            if bound is None:
                lower_bound[ii] = -numpy.inf
        pnew = numpy.maximum(pnew, 1.01*numpy.asarray(lower_bound))
    if upper_bound is not None:
        for ii,bound in enumerate(upper_bound):
            if bound is None:
                upper_bound[ii] = numpy.inf
        pnew = numpy.minimum(pnew, 0.99*numpy.asarray(upper_bound))
    return pnew

def make_fux_table_old(fid, ts, Q, tri_freq):
    """
    Make file of 1-fux for use in ancestral misidentification correction.

    fid: Filename to output to.
    ts: Expected number of substitutions per site between ingroup and outgroup.
    Q: Trinucleotide transition rate matrix. This should be a 64x64 matrix, in
       which entries are ordered using the code CGTA -> 0,1,2,3. For example, 
       ACT -> 3*16+0*4+2*1=50. The transition rate from ACT to AGT is then 
       entry 50,54.
    tri_freq: Dictionary in which each entry maps a trinucleotide to its 
              ancestral frequency. e.g. {'AAA': 0.01, 'AAC':0.012...}
              Note that should be the frequency in the entire region scanned
              for variation, not just sites where there are SNPs.
    """
    # Ensure that the rows of Q sum to zero.
    for ii,row in enumerate(Q):
        s = row.sum() - row[ii]
        row[ii] = -s

    eQhalf = scipy.linalg.matfuncs.expm(Q * ts/2.)
    if not hasattr(fid, 'write'):
        newfile = True
        fid = file(fid, 'w')

    outlines = []
    for ii,first in enumerate(code):
        for jj,second in enumerate(code):
            for kk,third in enumerate(code):
                for ll,outgroup in enumerate(code):
                    # These are the indices into Q and eQ
                    uind = 16*ii+4*jj+1*kk
                    xind = 16*ii+4*ll+1*kk

                    ## Note that the Q terms factor out in our final
                    ## calculation.
                    #Qux = Q[uind,xind]
                    #denomu = Q[uind].sum() - Q[uind,uind]

                    PMuUu, PMuUx = 0,0
                    # Equation 2 in HWB. We have to generalize slightly to
                    # calculate PMuUx.
                    for aa,alpha in enumerate(code):
                        aind = 16*ii+4*aa+1*kk

                        pia = tri_freq[first+alpha+third]
                        Pau = eQhalf[aind,uind]
                        Pax = eQhalf[aind,xind]

                        PMuUu += pia * Pau*Pau
                        PMuUx += pia * Pau*Pax

                    # This is fux. For a given SNP with actual ancestral state
                    # u, this is the probability that the outgroup will have u.
                    # Eqn 3 in HWB.
                    res = PMuUx/(PMuUu + PMuUx)
                    if outgroup == second:
                        res = 0
                    
                    outlines.append('%c%c%c %c %.6f' % (first,second,third,
                                                        outgroup, res))

    fid.write(os.linesep.join(outlines))
    if newfile:
        fid.close()

def make_fux_table(fid, ts, Q, tri_freq):
    """
    Make file of 1-fux for use in ancestral misidentification correction.

    fid: Filename to output to.
    ts: Expected number of substitutions per site between ingroup and outgroup.
    Q: Trinucleotide transition rate matrix. This should be a 64x64 matrix, in
       which entries are ordered using the code CGTA -> 0,1,2,3. For example, 
       ACT -> 3*16+0*4+2*1=50. The transition rate from ACT to AGT is then 
       entry 50,54.
    tri_freq: Dictionary in which each entry maps a trinucleotide to its 
              ancestral frequency. e.g. {'AAA': 0.01, 'AAC':0.012...}
              Note that should be the frequency in the entire region scanned
              for variation, not just sites where there are SNPs.
    """
    # Ensure that the *columns* of Q sum to zero.
    # That is the correct condition when Q_{i,j} is the rate from i to j.
    # This indicates a typo in Hernandez, Williamson, and Bustamante.
    for ii in range(Q.shape[1]):
        s = Q[:,ii].sum() - Q[ii,ii]
        Q[ii,ii] = -s

    eQhalf = scipy.linalg.matfuncs.expm(Q * ts/2.)
    if not hasattr(fid, 'write'):
        newfile = True
        fid = file(fid, 'w')

    outlines = []
    for first_ii,first in enumerate(code):
        for x_ii,x in enumerate(code):
            for third_ii,third in enumerate(code):
                # This the index into Q and eQ
                xind = 16*first_ii+4*x_ii+1*third_ii
                for u_ii,u in enumerate(code):
                    # This the index into Q and eQ
                    uind = 16*first_ii+4*u_ii+1*third_ii

                    ## Note that the Q terms factor out in our final
                    ## calculation, because for both PMuUu and PMuUx the final
                    ## factor in Eqn 2 is P(S={u,x}|M=u).
                    #Qux = Q[uind,xind]
                    #denomu = Q[uind].sum() - Q[uind,uind]

                    PMuUu, PMuUx = 0,0
                    # Equation 2 in HWB. We have to generalize slightly to
                    # calculate PMuUx. In calculate PMuUx, we're summing over
                    # alpha the probability that the MRCA was alpha, and it
                    # substituted to x on the outgroup branch, and it
                    # substituted to u on the ingroup branch, and it mutated to
                    # x in the ingroup (conditional on it having mutated in the
                    # ingroup). Note that the mutation to x condition cancels
                    # in fux, so we don't bother to calculate it.
                    for aa,alpha in enumerate(code):
                        aind = 16*first_ii+4*aa+1*third_ii

                        pia = tri_freq[first+alpha+third]
                        Pau = eQhalf[aind,uind]
                        Pax = eQhalf[aind,xind]

                        PMuUu += pia * Pau*Pau
                        PMuUx += pia * Pau*Pax

                    # This is 1-fux. For a given SNP with actual ancestral state
                    # u and derived allele x, this is 1 minus the probability
                    # that the outgroup will have u.
                    # Eqn 3 in HWB.
                    res = 1 - PMuUu/(PMuUu + PMuUx)
                    # These aren't SNPs, so we can arbitrarily set them to 0
                    if u == x:
                        res = 0
                    
                    outlines.append('%c%c%c %c %.6f' % (first,x,third,u,res))

    fid.write(os.linesep.join(outlines))
    if newfile:
        fid.close()

def zero_diag(Q):
    """
    Copy of Q altered such that diagonal entries are all 0.
    """
    Q_nodiag = Q.copy()
    for ii in range(Q.shape[0]):
        Q_nodiag[ii,ii] = 0
    return Q_nodiag

def tri_freq_dict_to_array(tri_freq_dict):
    tripi = numpy.zeros(64)
    for ii,left in enumerate(code):
        for jj,center in enumerate(code):
            for kk,right in enumerate(code):
                row = ii*16 + jj*4 + kk
                tripi[row] = tri_freq_dict[left+center+right]
    return tripi

def total_instantaneous_rate(Q, pi):
    """
    Total instantaneous substitution rate.
    """
    Qzero = zero_diag(Q)
    return numpy.dot(pi, Qzero).sum()

def make_data_dict(filename):
    """
    Parse SNP file and store info in a properly formatted dictionary.

    filename: Name of file to work with.

    This is specific to the particular data format described on the wiki. 
    Modification for other formats should be straightforward.

    The file can be zipped (extension .zip) or gzipped (extension .gz). If 
    zipped, there must be only a single file in the zip archive.
    """
    if os.path.splitext(filename)[1] == '.gz':
        import gzip
        f = gzip.open(filename)
    elif os.path.splitext(filename)[1] == '.zip':
        import zipfile
        archive = zipfile.ZipFile(filename)
        namelist = archive.namelist()
        if len(namelist) != 1:
            raise ValueError('Must be only a single data file in zip '
                             'archive: %s' % filename)
        f = archive.open(namelist[0])
    else:
        f = open(filename)

    # Skip to the header
    while True:
        header = f.readline()
        if not header.startswith('#'):
            break

    allele2_index = header.split().index('Allele2')

    # Pull out our pop ids
    pops = header.split()[3:allele2_index]

    # The empty data dictionary
    data_dict = {}

    # Now walk down the file
    for line in f:
        if line.startswith('#'):
            continue
        # Split the into fields by whitespace
        spl = line.split()

        data_this_snp = {}

        # We convert to upper case to avoid any issues with mixed case between
        # SNPs.
        data_this_snp['context'] = spl[0].upper()
        data_this_snp['outgroup_context'] = spl[1].upper()
        data_this_snp['outgroup_allele'] = spl[1][1].upper()
        data_this_snp['segregating'] = spl[2].upper(),spl[allele2_index].upper()

        calls_dict = {}
        for ii,pop in enumerate(pops):
            calls_dict[pop] = int(spl[3+ii]), int(spl[allele2_index+1+ii])
        data_this_snp['calls'] = calls_dict

        # We name our SNPs using the final columns
        snp_id = '_'.join(spl[allele2_index+1+len(pops):])

        data_dict[snp_id] = data_this_snp

    return data_dict
