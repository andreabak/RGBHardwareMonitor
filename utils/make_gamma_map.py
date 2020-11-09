def make_gamma_map(in_range, out_range, gamma):
    return [int(out_range * (float(i) / in_range) ** gamma) for i in range(in_range)]


def max_delta(vmap):
    return max(v-vmap[i] for i, v in enumerate(vmap[1:]))


def format_map(vmap, cols=16):
    pad = len(str(max(vmap)))
    return ',\n'.join(', '.join(('{:'+str(pad)+'d}').format(v) for v in row)
                      for row in [vmap[i:i + cols] for i in range(0, len(vmap), cols)])
