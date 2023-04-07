
from typing import List
from xml.etree import ElementTree as ET

import click

from launchable.commands.record.case_event import CaseEvent
from launchable.testpath import TestPath

from . import launchable


def build_path(module: str, test_case: str, test: str):
    return [
        {"type": "Module", "name": module},
        {"type": "TestCase", "name": test_case},
        {"type": "Test", "name": test},
    ]


def parse_func(p: str):
    """  # noqa: E501
    # sample report format
    success case:
    <Module name="CtsAbiOverrideHostTestCases" abi="arm64-v8a" runtime="1171" done="true" pass="1" total_tests="1">
      <TestCase name="android.abioverride.cts.AbiOverrideTest">
        <Test result="pass" name="testAbiIs32bit" />
      </TestCase>
    </Module>

    failure case:
    <Module name="CtsAccountManagerTestCases" abi="arm64-v8a" runtime="13414" done="false" pass="2" total_tests="151">
      <Reason message="Instrumentation run failed due to 'Process crashed.'" error_name="INSTRUMENTATION_CRASH" error_code="520200" />
      <TestCase name="android.accounts.cts.AbstractAuthenticatorTests">
        <Test result="fail" name="testFinishSessionAndStartAddAccountSessionDefaultImpl">
          <Failure message="android.accounts.OperationCanceledException&#13;">
            <StackTrace>android.accounts.OperationCanceledException
          at android.accounts.AccountManager$AmsTask.internalGetResult(AccountManager.java:2393)
          at android.accounts.AccountManager$AmsTask.getResult(AccountManager.java:2422)
          at android.accounts.AccountManager$AmsTask.getResult(AccountManager.java:2337)
          at android.accounts.cts.AbstractAuthenticatorTests.testFinishSessionAndStartAddAccountSessionDefaultImpl(AbstractAuthenticatorTests.java:165)
            </StackTrace>
          </Failure>
        </Test>
      </TestCase>
    </Module>
    """
    class TestResult:
        def __init__(self, test_case_name: str, test_name: str, result: str, stdout: str, stderr: str):
            self.test_case_name = test_case_name
            self.test_name = test_name
            self.result = result
            self.stdout = stdout
            self.stderr = stderr

        def case_event_status(self):
            if self.result == "fail":
                return CaseEvent.TEST_FAILED
            elif self.result == "ASSUMPTION_FAILURE" or self.result == "IGNORED":
                return CaseEvent.TEST_SKIPPED

            return CaseEvent.TEST_PASSED

    events = []
    tree = ET.parse(p)

    for module in tree.iter('Module'):
        test_results: List[TestResult] = []
        total_duration = module.get("runtime", "0")
        module_name = module.get("name", "")

        for test_case in module.iter("TestCase"):
            test_case_name = test_case.get('name', "")

            for test in test_case.iter("Test"):
                result = test.get('result', "")
                test_name = test.get("name", "")
                stdout = ""
                stderr = ""

                failure = test.find('Failure')
                if failure:
                    stack_trace = ""
                    stack_trace_element = failure.find("StackTrace")
                    if stack_trace_element is not None:
                        stack_trace = str(stack_trace_element.text)

                    stdout = failure.get("message", "")
                    stderr = stack_trace

                test_results.append(TestResult(
                    test_case_name=test_case_name,
                    test_name=test_name,
                    result=result,
                    stdout=stdout,
                    stderr=stderr))

        if len(test_results) == 0:
            continue

        test_duration_msec_per_test = int(total_duration) / len(test_results)

        for test_result in test_results:  # type: TestResult
            if module_name == "" or test_result.test_case_name == "" or test_result.test_name == "":
                continue

            events.append(CaseEvent.create(
                test_path=build_path(module_name, test_result.test_case_name, test_result.test_name),
                duration_secs=float(test_duration_msec_per_test / 1000),
                status=test_result.case_event_status(),
                stdout=test_result.stdout,
                stderr=test_result.stderr,
            ))

    return (x for x in events)


@click.argument('reports', required=True, nargs=-1)
@launchable.record.tests
def record_tests(client, reports):
    """
    Beta: Report test result that Compatibility Test Suite (CTS) produced
    """
    for r in reports:
        client.report(r)

    client.parse_func = parse_func
    client.run()


@launchable.subset
def subset(client):
    """
    Beta: Produces test list from previous test sessions for Compatibility Test Suite (CTS)
    """
    if not client.is_get_tests_from_previous_sessions:
        click.echo(click.style(
            "ERROR: cts profile supports only Zero Input Subsetting (ZIS). Please use `--get-tests-from-previous-sessions` option for subsetting",  # noqa E501
            fg="red"),
            err=True)
        exit(1)

    include_option = "--include-filter"
    exclude_option = "--exclude-filter"

    def formatter(test_path: TestPath):
        module = ""
        test_case = ""
        for path in test_path:
            t = path.get('type', '')
            n = path.get('name', '')

            if t == "Module":
                module = n
            elif t == "TestCase":
                test_case = n

        if module == "" or test_case == "":
            return

        option = include_option
        if client.is_output_exclusion_rules:
            option = exclude_option

        return "{option} \"{module} {test_case}\"".format(option=option, module=module, test_case=test_case)

    client.formatter = formatter
    client.separator = " "
    client.run()
