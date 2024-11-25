from __future__ import annotations
import typing as tp

from nnodes import Directory

if tp.TYPE_CHECKING:
    from .typing import Par_file, Specfem


def getsize(d: Directory):
    """Number of processors to run the solver."""
    pars = getpars(d)

    if 'NPROC_XI' in pars and 'NPROC_ETA' in pars and 'NCHUNKS' in pars:
        return pars['NPROC_XI'] * pars['NPROC_ETA'] * pars['NCHUNKS']
    
    raise RuntimeError('not dimension in Par_file')


def xspecfem(node: Specfem):
    """Add task to call xspecfem3D."""
    node.add_mpi('bin/xspecfem3D', getsize, 1, data={'prober': probe_solver})


def xmeshfem(node: Specfem):
    """Add task to call xmeshfem3D."""
    if node.path_mesh:
        node.add(node.ln, name='link_mesh', args=(node.rel(node.path_mesh, 'DATABASES_MPI/*'), 'DATABASES_MPI'))
    
    else:
        node.add_mpi('bin/xmeshfem3D', getsize, data={'prober': probe_mesher})


def getpars(d: Directory) -> Par_file:
    """Get entries in Par_file."""
    pars: Par_file = {}

    if not d.has('DATA/Par_file'):
        d = Directory(tp.cast(tp.Any, d).path_specfem)

    for line in d.readlines('DATA/Par_file'):
        if '=' in line:
            keysec, valsec = line.split('=')[:2]
            key = keysec.split()[0]
            val = valsec.split('#')[0].split()[0]

            if val == '.true':
                pars[key] = True
            
            elif val == '.false.':
                pars[key] = False
            
            elif val.isnumeric():
                pars[key] = int(val)
            
            else:
                try:
                    pars[key] = float(val.replace('D', 'E').replace('d', 'e'))
                
                except:
                    pars[key] = val
    
    return pars


def setpars(d: Directory, pars: Par_file):
    """Set entries in Par_file."""
    lines = d.readlines('DATA/Par_file')

    # update lines from par
    for i, line in enumerate(lines):
        if '=' in line:
            keysec = line.split('=')[0]
            key = keysec.split()[0]

            if key in pars and pars[key] is not None:
                val = pars[key]

                if isinstance(val, bool):
                    val = f'.{str(val).lower()}.'

                elif isinstance(val, float):
                    if len('%f' % val) < len(f'{val}'):
                        val = '%fd0' % val

                    else:
                        val = f'{val}d0'

                lines[i] = f'{keysec}= {val}'

    d.writelines(lines, 'DATA/Par_file')


def probe_solver(d: Specfem) -> float:
    """Prober of solver progress."""
    from math import ceil

    if not d.has(out := 'OUTPUT_FILES/output_solver.txt'):
        return 0.0
    
    lines = d.readlines(out)
    lines.reverse()

    for line in lines:
        if 'End of the simulation' in line:
            return 1.0

        if 'We have done' in line:
            words = line.split()
            done = False

            for word in words:
                if word == 'done':
                    done = True

                elif word and done:
                    return ceil(float(word)) / 100

    return 0.0


def probe_mesher(d: Specfem) -> float:
    """Prober of mesher progress."""
    ntotal = 0
    nl = 0

    if not d.has(out_file := 'OUTPUT_FILES/output_mesher.txt'):
        return 0.0
    
    lines = d.readlines(out_file)

    for line in lines:
        if ' out of ' in line:
            if ntotal == 0:
                ntotal = int(line.split()[-1]) * 2

            if nl < ntotal:
                nl += 1

        if 'End of mesh generation' in line:
            return 1.0

    if ntotal == 0:
        return 0.0

    return (nl - 1) / ntotal
