import time, json
import heapq, subprocess

if __name__ == '__main__':
    subprocess.run('./step1_register.sh', capture_output=True, check=True, shell=True)
    subprocess.run('./step2_launch.sh', capture_output=True, check=True, shell=True)
    for i in range(1, 3):
        processes = []
        f = open('traffic_profile' + str(i) + '.json')
        tests = json.load(f)["profiles"]
        f.close()

        min_heap = []

        for test in tests:
            for flow in test['flows']:
                heapq.heappush(min_heap, (
                    flow['start_time'], flow['end_time'], flow['num_flows'],
                    test["src_container"], test["dst_container"], test['dst_ip']))

        t = 0
        while len(min_heap) > 0:
            top = heapq.heappop(min_heap)
            time.sleep(top[0] - t)
            if i == 1:
                subprocess.Popen('docker exec ' + top[4] + ' iperf3 -s',
                                 shell=True, stdout=subprocess.PIPE)
                time.sleep(1)
            processes.append(subprocess.Popen(
                'docker exec ' + top[3] + ' iperf3 -c ' + top[5] + ' -P ' + str(top[2]) + ' -t ' + str(
                    top[1] - top[0]), shell=True, stdout=subprocess.PIPE))
            t = top[0]

        for p in processes:
            p.wait()

        list = ['src1', 'dst1', 'src2', 'dst2', 'fw0', 'nat0', 'nat1']
        list2 = ['fw1', 'nat2', 'nat3']
        for name in list:
            print(name)
            subprocess.run('docker exec ' + name + ' netstat -i', check=True, shell=True)
            print(' ')

        if i == 2:
            for name in list2:
                print(name)
                subprocess.run('docker exec ' + name + ' netstat -i', check=True, shell=True)
                print(' ')

        print('br1')
        subprocess.run('sudo ovs-ofctl dump-flows ovs-br1', check=True, shell=True)
        print('\nbr2')
        subprocess.run('sudo ovs-ofctl dump-flows ovs-br2', check=True, shell=True)

        if i == 1:
            subprocess.run('./step3_scaleup.sh', capture_output=True, check=True,
                           shell=True)
            print('----------scale up-----------')
