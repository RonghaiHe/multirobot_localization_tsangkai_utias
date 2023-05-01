import time
import utils as u


def main(args):
    '''
    Main function that analyzes then plots every specified algorithm for every specified dataset.
    '''

    # extract args
    path, datasets, algorithms, comm_type, comm_range, comm_rate, comm_prob_fail, dt, offset, duration = \
        args['path'], args['datasets'], args['algorithms'], args['comm_type'], args['comm_range'], args['comm_rate'], args['comm_prob_fail'], args['dt'], args['offset'], args['duration']

    print('Loaded Settings:')
    print('\tUTIAS MRCLAM Path: ' + str(path))
    print('\tDataset(s): ' + str(datasets))
    print('\tAlgorithm(s): ' + str(algorithms))
    print('\tCommunication Type: ' + str(comm_type))
    print('\tCommunication Range: ' + str(comm_range) + ' meters')
    print('\tCommunication Rate: ' + str(comm_rate) + ' seconds')
    print('\tCommunication Failure Probability: ' + str(comm_prob_fail))
    print('\tTime Precision: ' + str(dt) + ' seconds / timestep')
    print('\tTime Offset: ' + str(offset) + ' seconds')
    print('\tTime Duration: ' + str(duration) + ' seconds')
    print('')

    # start
    exec_start = time.time()

    # load datasets
    UTIAS = u.load_datasets(path, datasets)

    # execute algorithms on datasets
    results = u.execute(UTIAS, algorithms, comm_type, comm_range, comm_rate, comm_prob_fail, dt, offset, duration)

    # plot the results
    u.analyze(results, [comm_type, comm_range, comm_rate, comm_prob_fail, dt, offset, duration], save=True)

    # end
    exec_end = time.time()
    hours, minutes, seconds = u.exec_time(exec_start, exec_end)
    print("Total execution time: {:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))


if __name__ == '__main__':
    # change for dict, just for debug
    args = {'path': '/data/herh/utias/',
            'datasets': [9],
            'algorithms': ['lsci', 'lscen', 'lssci', 'lsbda', 'gsci'],
            'comm_type': 'all', 
            'comm_range': 20, 
            'comm_rate': 0.2, 
            'comm_prob_fail': 0, 
            'dt': 0.2, 
            'offset': 1500, 
            'duration': 25
            }

    main(args)

