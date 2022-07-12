# https://stackoverflow.com/questions/20360686/compulsory-usage-of-if-name-main-in-windows-while-using-multiprocessi
if __name__ == '__main__':
    import torch
    import xarray as xr
    import argparse
    import json

    from pyqg_generative.models.mean_var_model import MeanVarModel, OLSModel
    from pyqg_generative.models.parameterization import EDDY_PARAMS, JET_PARAMS, ReferenceModel, TrivialStochastic
    import pyqg_subgrid_experiments as pse

    def read_ds(path):
        ds = pse.Dataset(path)
        ds['psi'] = ds.streamfunction
        #ds = ds.drop_vars('q_forcing_advection').rename({'q_forcing_total': 'q_forcing_advection'})
        return ds

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='TrivialStochastic')
    args = parser.parse_args()
    print(args)
    with open('args.json', 'w') as f:
        json.dump(args.__dict__, f, indent=2)

    inputs = ['q']
    targets = ['q_forcing_advection']

    if args.model == 'TrivialStochastic':
        model = TrivialStochastic(inputs, targets)
    elif args.model == 'MeanVarModel':
        model = MeanVarModel(inputs, targets)
    elif args.model == 'lowres':
        model = ReferenceModel(inputs, targets)
    elif args.model == 'OLSModel':
        model = OLSModel(inputs, targets)

    test = read_ds("/scratch/zanna/data/pyqg/data/test/*.nc")
    transfer = read_ds("/scratch/zanna/data/pyqg/data/transfer/*.nc")

    try:
        model = torch.load('net_state', map_location='cpu')
        print('Model is loaded from the disk')
    except:
        train = read_ds("/scratch/zanna/data/pyqg/data/train/*.nc")
        model.fit(train, test)
        torch.save(model, 'net_state')
        del train

    model.test_offline(test).to_netcdf('offline_test.nc')
    model.test_offline(transfer).to_netcdf('offline_transfer.nc')

    del test
    del transfer

    test_highres = xr.open_dataset('/scratch/pp2681/pyqg_generative/highres/online_eddy.nc')
    transfer_highres = xr.open_dataset('/scratch/pp2681/pyqg_generative/highres/online_jet.nc')

    if args.model in ['lowres', 'OLSModel']:
        model.test_ensemble(test_highres, EDDY_PARAMS).to_netcdf('ensemble_test.nc')
        model.test_ensemble(transfer_highres, JET_PARAMS).to_netcdf('ensemble_transfer.nc')

        model.test_online(EDDY_PARAMS).to_netcdf('online_test.nc')
        model.test_online(JET_PARAMS).to_netcdf('online_transfer.nc')
    else:
        for sampling in ['constant', 'AR1']:
            for nsteps in [1, 6, 12]:
                model.test_ensemble(test_highres, EDDY_PARAMS, 
                    sampling_type=sampling, nsteps=nsteps).to_netcdf('ensemble_test_'+sampling+'_'+str(nsteps)+'.nc')
                model.test_ensemble(transfer_highres, JET_PARAMS, 
                    sampling_type=sampling, nsteps=nsteps).to_netcdf('ensemble_transfer_'+sampling+'_'+str(nsteps)+'.nc')

                model.test_online(EDDY_PARAMS, 
                    sampling_type=sampling, nsteps=nsteps).to_netcdf('online_test_'+sampling+'_'+str(nsteps)+'.nc')
                model.test_online(JET_PARAMS, 
                    sampling_type=sampling, nsteps=nsteps).to_netcdf('online_transfer_'+sampling+'_'+str(nsteps)+'.nc')